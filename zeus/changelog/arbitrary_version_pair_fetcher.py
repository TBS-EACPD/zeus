from functools import reduce

from django.db.models import (
    BooleanField,
    CharField,
    F,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.utils.functional import cached_property

from .util import get_diffable_fields_for_model


class ArbitraryVersionPairFetcher:
    """
        given a list of queryset pairs (one pair per model)
        outputs a list of {right_id, left_id, eternal_id, model}
        automatically filters out record where right_id == left_id
    """

    def __init__(self, qs_pairs):
        self.qs_pairs = qs_pairs

    @cached_property
    def models_by_name(self):
        models_by_name = {
            qs_pair[0].model.live_model.__name__: qs_pair[0].model
            for qs_pair in self.qs_pairs
        }
        return models_by_name

    def _get_union_for_models(self, querysets):
        model_querysets = [
            qs.annotate(
                model_name=Value(qs.model.live_model.__name__, CharField())
            ).values("model_name", "id", "eternal_id")
            for qs in querysets
        ]

        unionize = lambda qs1, qs2: qs1.union(qs2)
        unioned_qs = reduce(unionize, model_querysets)
        return unioned_qs

    def _index_qs(self, qs):
        indexed = {}
        for record in qs:
            model = self.models_by_name[record["model_name"]]
            eternal_id = record["eternal_id"]
            indexed[(model, eternal_id)] = record["id"]

        return indexed

    def get_version_pairs(self):
        left_querysets = [p[0] for p in self.qs_pairs]
        right_querysets = [p[1] for p in self.qs_pairs]

        left_union = self._get_union_for_models(left_querysets)
        right_union = self._get_union_for_models(right_querysets)

        left_minus_right = self._index_qs(left_union.difference(right_union))
        right_minus_left = self._index_qs(right_union.difference(left_union))

        final_values = []
        for model, eternal_id in {*left_minus_right.keys(), *right_minus_left.keys()}:
            right_id = right_minus_left.get((model, eternal_id), None)
            left_id = left_minus_right.get((model, eternal_id), None)
            final_values.append(
                {
                    "right_id": right_id,
                    "left_id": left_id,
                    "model": model,
                    "eternal_id": eternal_id,
                }
            )

        return final_values
