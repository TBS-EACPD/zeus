import importlib

from django.db import connection, models, transaction
from django.db.models.base import ModelBase
from django.forms import ModelForm

import pytest

from zeus.versioning.core import VersionModel


@pytest.fixture(scope="module")
def register_model(django_db_setup, django_db_blocker):
    registered_models = []

    def register(model_cls):
        registered_models.append(model_cls)
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(model_cls)

    with django_db_blocker.unblock():
        try:
            with transaction.atomic():
                yield register

                with connection.schema_editor() as schema_editor:
                    for model in registered_models:
                        schema_editor.delete_model(model)

                raise Exception(
                    "any exception will cause the transaction to be rolled back"
                )

        # pylint: disable="broad-except"
        except Exception:
            pass


# we use module-scope because django complains if you register the same model twice
@pytest.fixture(scope="module")
def common(register_model):

    # This can be any module in <installed_app>
    # when extracting to own package
    # tests will against on an 'example project' with an empty app
    module = "django_sample.models"

    class MyGroupLookup(models.Model):
        __module__ = module
        name = models.CharField(max_length=20)

    class MyLiveModel(models.Model):
        __module__ = module
        name = models.CharField(max_length=20)
        groups = models.ManyToManyField(MyGroupLookup)
        favorite_group = models.ForeignKey(
            MyGroupLookup, null=False, on_delete=models.CASCADE
        )

    class MyModelVersion(VersionModel):
        live_model = MyLiveModel
        __module__ = module

    register_model(MyGroupLookup)
    register_model(MyLiveModel)
    register_model(MyModelVersion)

    group_1 = MyGroupLookup.objects.create(name="group1")
    group_2 = MyGroupLookup.objects.create(name="group2")
    group_3 = MyGroupLookup.objects.create(name="group3")

    class NameSpace:
        group1 = group_1
        group2 = group_2
        group3 = group_3
        GroupLookup = MyGroupLookup
        LiveModel = MyLiveModel
        VersionModel = MyModelVersion

    return NameSpace


def test_create_dynamic_model(common):

    live_inst_1 = common.LiveModel.objects.create(name="v1", favorite_group=common.group1)
    assert live_inst_1.versions.count() == 1
    v1 = live_inst_1.versions.last()
    assert v1.eternal == live_inst_1
    assert v1.name == "v1"
    assert v1.favorite_group_id == common.group1.id
    assert v1.groups == []

    live_inst_1.reset_version_attrs()
    live_inst_1.groups.add(common.group1)
    live_inst_1.save()
    assert live_inst_1.versions.count() == 2
    v2 = live_inst_1.versions.last()
    assert v2.groups == [common.group1.pk]

    v1.refresh_from_db()
    assert v1.groups == []


def test_m2m_add(common):
    obj = common.LiveModel.objects.create(name="v1", favorite_group=common.group1)
    obj.reset_version_attrs()

    obj.groups.add(common.group1)

    # check og version wasn't modified
    assert obj.versions.count() == 2
    assert obj.versions.first().groups == []
    assert obj.versions.last().groups == [common.group1.pk]


def test_m2m_rm(common):
    obj = common.LiveModel.objects.create(name="v1", favorite_group=common.group1)
    obj.groups.add(common.group1)

    assert obj.versions.count() == 1
    assert obj.versions.last().groups == [common.group1.pk]

    obj.reset_version_attrs()
    obj.groups.remove(common.group1)

    # check og version wasn't modified
    assert obj.versions.count() == 2
    assert obj.versions.first().groups == [common.group1.pk]
    assert obj.versions.last().groups == []


def test_m2m_add_and_rm(common):
    obj = common.LiveModel.objects.create(name="v1", favorite_group=common.group1)
    obj.groups.add(common.group1)

    assert obj.versions.count() == 1
    assert obj.versions.last().groups == [common.group1.pk]

    obj.reset_version_attrs()
    obj.groups.remove(common.group1)
    obj.groups.add(common.group2)

    assert obj.versions.count() == 2
    assert obj.versions.first().groups == [common.group1.pk]
    assert obj.versions.last().groups == [common.group2.pk]


def test_create_then_m2m_edit_doesnt_add_version(common):
    obj = common.LiveModel.objects.create(name="v1", favorite_group=common.group1)
    obj.groups.add(common.group1)
    assert obj.versions.count() == 1
    assert obj.versions.last().groups == [common.group1.pk]


def test_scalar_edit_then_m2m_edit_only_adds_one_version(common):
    obj = common.LiveModel.objects.create(name="name1", favorite_group=common.group1)
    obj.reset_version_attrs()

    obj.name = "name2"
    obj.save()
    obj.groups.add(common.group1)

    assert obj.versions.count() == 2
    assert obj.versions.first().name == "name1"
    assert obj.versions.first().groups == []
    assert obj.versions.last().name == "name2"
    assert obj.versions.last().groups == [common.group1.pk]


def test_m2m_change_then_scalar_change_only_adds_one_version(common):
    obj = common.LiveModel.objects.create(name="name1", favorite_group=common.group1)
    obj.reset_version_attrs()

    obj.groups.add(common.group1)
    obj.name = "name2"
    obj.save()

    assert obj.versions.count() == 2
    assert obj.versions.first().name == "name1"
    assert obj.versions.first().groups == []
    assert obj.versions.last().name == "name2"
    assert obj.versions.last().groups == [common.group1.pk]


def test_create_via_model_form(common):
    class Form(ModelForm):
        class Meta:
            model = common.LiveModel
            fields = [
                "name",
                "favorite_group",
                "groups",
            ]

    form_data = {
        "name": "v1",
        "favorite_group": common.group1.pk,
        "groups": [common.group1.pk],
    }

    obj = Form(form_data).save()
    assert obj.pk
    assert obj.versions.count() == 1
    v1 = obj.versions.last()
    assert v1.name == "v1"
    assert v1.groups == [common.group1.pk]
