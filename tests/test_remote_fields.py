import mock
from unittest import TestCase

import httpretty
from rest_framework import serializers

from remotefields import RemoteFieldsModelSerializerMixin, RemoteField
from rest_client.client import Client
from tests.models import ModelForTest


TESTING_HOST = 'http://127.0.0.1:9191/'
TESTING_USER = 'NoBody'
TESTING_PASSWORD = 'P4ssw0rd!'

client = Client(TESTING_HOST, TESTING_USER, TESTING_PASSWORD)


class TestSerializer(RemoteFieldsModelSerializerMixin,
                     serializers.ModelSerializer):
    thing = RemoteField(
        source='thing_id', remote_sources=('id', 'name',),
        endpoints={
            'list': client.some.endpoint_list,
            'detail': client.some.endpoint_detail
        }
    )

    class Meta:
        model = ModelForTest
        fields = ('id', 'thing')


class RemoteFieldsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(RemoteFieldsTest, cls).setUpClass()
        cls.endpoints = {
            'some__endpoint_detail': 'some/endpoint-detail/',
            'some__endpoint_list': 'some/endpoint-list/'
        }

        httpretty.enable()
        httpretty.register_uri(
            httpretty.GET,
            'http://127.0.0.1:9191/some/endpoint-detail/?pk=2001',
            status=200,
            body='{"id": 2001, "name": "Name of the thing"}'
        )
        httpretty.register_uri(
            httpretty.GET,
            'http://127.0.0.1:9191/some/endpoint-list/',
            status=200,
            body=('[{"id": 2002, "name": "Name of the thing"}, '
                  '{"id": 2003, "name": "Name of another thing"}]')
        )
        httpretty.register_uri(
            httpretty.GET,
            'http://127.0.0.1:9191/some/endpoint-detail/?pk=0',
            status=400,
            body='{"detail": "Invalid request"}'
        )

    @classmethod
    def tearDownClass(cls):
        super(RemoteFieldsTest, cls).tearDownClass()
        httpretty.disable()
        httpretty.reset()

    def tearDown(self):
        super(RemoteFieldsTest, self).tearDown()
        ModelForTest.objects.all().delete()

    def test_empty_data(self):
        """
        Try to serialize an empty set of data, expect an error to be raised
        """
        serializer = TestSerializer()

        with self.assertRaises(ValueError):
            with mock.patch.dict(
                    'rest_client.client.ENDPOINTS', self.endpoints):
                serializer.data

    def test_valid_model_instance(self):
        """
        Serialize a valid model with a remote field and check the result
        """
        model_instance = ModelForTest(thing_id=2001)
        model_instance.save()
        serializer = TestSerializer(model_instance)
        expected = {'id': 1,
                    'thing': {'id': 2001, 'name': u'Name of the thing'}}

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEquals(result, expected)

    def test_valid_model_queryset(self):
        """
        Serialize a queryset with a remote field and check the result
        """
        ModelForTest(thing_id=2002).save()
        ModelForTest(thing_id=2003).save()
        query = ModelForTest.objects.all()
        serializer = TestSerializer(query)
        expected = [
            {'id': 1, 'thing': {'id': 2002, 'name': 'Name of the thing'}},
            {'id': 2, 'thing': {'id': 2003, 'name': 'Name of another thing'}}
        ]

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEquals(result, expected)
