from django.db import models


class ModelForTest(models.Model):
    thing_id = models.IntegerField()


class ParentModelForTest(models.Model):
    test_instance = models.ForeignKey(ModelForTest)
    test_instances = models.ManyToManyField(ModelForTest, related_name='+')
