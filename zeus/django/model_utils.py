from django.db import models

neverQ = models.Q(pk=None)
anyQ = ~neverQ
