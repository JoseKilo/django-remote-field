import mock
import re
from unittest import TestCase

import httpretty
from rest_framework import serializers

from remotefields import RemoteFieldsModelSerializerMixin, RemoteField
from rest_client.client import Client
from tests.models import ModelForTest, ParentModelForTest


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


class ParentTestSerializer(RemoteFieldsModelSerializerMixin,
                           serializers.ModelSerializer):
    test_instance = TestSerializer()

    class Meta:
        model = ParentModelForTest
        fields = ('id', 'test_instance')


class ParentWithManyTestSerializer(RemoteFieldsModelSerializerMixin,
                                   serializers.ModelSerializer):
    test_instances = TestSerializer(many=True)

    class Meta:
        model = ParentModelForTest
        fields = ('id', 'test_instances')


class TestSerializerWithFlatField(RemoteFieldsModelSerializerMixin,
                                  serializers.ModelSerializer):
    thing_name = RemoteField(
        source='thing_id', remote_sources=('name',), flat=True,
        endpoints={
            'list': client.some.endpoint_list,
            'detail': client.some.endpoint_detail
        }
    )

    class Meta:
        model = ModelForTest
        fields = ('id', 'thing_name')


class RemoteFieldsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super(RemoteFieldsTest, cls).setUpClass()
        cls.endpoints = {
            'some__endpoint_detail': 'some/endpoint-detail/',
            'some__endpoint_list': 'some/endpoint-list/'
        }

        httpretty.enable()

        for id in (2001, 2004, 2005):
            httpretty.register_uri(
                httpretty.GET,
                re.compile('http://127.0.0.1:9191/some/endpoint-detail/'
                           '\?pk={}'.format(id)),
                status=200,
                body='{{"id": {}, "name": "Name of the thing"}}'.format(id),
                match_querystring=True
            )

        httpretty.register_uri(
            httpretty.GET,
            'http://127.0.0.1:9191/some/endpoint-list/',
            status=200,
            body=('['
                  '{"id": 2001, "name": "Name of the thing"}, '
                  '{"id": 2002, "name": "Name of the thing"}, '
                  '{"id": 2003, "name": "Name of another thing"}, '
                  '{"id": 2004, "name": "Name of the thing"}, '
                  '{"id": 2005, "name": "Name of the thing"}'
                  ']')
        )
        httpretty.register_uri(
            httpretty.GET,
            re.compile('http://127.0.0.1:9191/some/endpoint-detail/\?pk=0'),
            status=400,
            body='{"detail": "Invalid request"}',
            match_querystring=True
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
        expected = {'thing': None}

        with mock.patch.dict(
                'rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEqual(result, expected)

    def test_valid_model_instance(self):
        """
        Serialize a valid model with a remote field and check the result
        """
        model_instance = ModelForTest(thing_id=2001)
        model_instance.save()
        serializer = TestSerializer(model_instance)
        expected = {'id': 1,
                    'thing': {'id': 2001, 'name': 'Name of the thing'}}

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEqual(result, expected)

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

        self.assertEqual(result, expected)

    def test_empty_data_with_flat_field(self):
        """
        Try to serialize an empty set of data, expect an error to be raised
        """
        serializer = TestSerializerWithFlatField()
        expected = {'thing_name': None}

        with mock.patch.dict(
                'rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEqual(result, expected)

    def test_valid_model_instance_with_flat_field(self):
        """
        Serialize a valid model with a remote field and check the result
        """
        model_instance = ModelForTest(thing_id=2001)
        model_instance.save()
        serializer = TestSerializerWithFlatField(model_instance)
        expected = {'id': 1, 'thing_name': 'Name of the thing'}

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEqual(result, expected)

    def test_valid_model_queryset_with_flat_field(self):
        """
        Serialize a queryset with a remote field and check the result
        """
        ModelForTest(thing_id=2002).save()
        ModelForTest(thing_id=2003).save()
        query = ModelForTest.objects.all()
        serializer = TestSerializerWithFlatField(query)
        expected = [
            {'id': 1, 'thing_name': 'Name of the thing'},
            {'id': 2, 'thing_name': 'Name of another thing'}
        ]

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertEqual(result, expected)

    def test_valid_model_instance_with_nested(self):
        """
        Serialize a valid model with a nested serializer and check the result
        """
        model_instance = ModelForTest.objects.create(thing_id=2001)
        parent_model_instance = ParentModelForTest.objects.create(
            test_instance=model_instance)
        serializer = ParentTestSerializer(parent_model_instance)
        expected = {'id': 1,
                    'test_instance': {
                        'id': 1,
                        'thing': {'id': 2001, 'name': 'Name of the thing'}}}

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertDictEqual(result, expected)

    def test_valid_model_queryset_with_nested(self):
        """
        Serialize a queryset with a nested serializer and check the result
        """
        model_instance_1 = ModelForTest.objects.create(thing_id=2004)
        model_instance_2 = ModelForTest.objects.create(thing_id=2005)
        obj = ParentModelForTest.objects.create(test_instance=model_instance_1)
        obj.test_instances.add(model_instance_2)
        ParentModelForTest.objects.create(test_instance=model_instance_2)
        query = ParentModelForTest.objects.all()
        serializer = ParentTestSerializer(query)
        expected = [
            {'id': 1,
             'test_instance': {
                 'id': 1, 'thing': {'id': 2004, 'name': 'Name of the thing'}}},
            {'id': 2,
             'test_instance': {
                 'id': 2, 'thing': {'id': 2005, 'name': 'Name of the thing'}}},
        ]

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertDictEqual(result[0], expected[0])
        self.assertDictEqual(result[1], expected[1])

    def test_valid_model_instance_with_nested_many(self):
        """
        Serialize a valid model with a nested serializer and check the result
        """
        model_instance = ModelForTest.objects.create(thing_id=2001)
        parent_model_instance = ParentModelForTest.objects.create(
            test_instance=model_instance)
        serializer = ParentWithManyTestSerializer(parent_model_instance)
        expected = {'id': 1,
                    'test_instances': []}

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertDictEqual(result, expected)

    def test_valid_model_queryset_with_nested_many(self):
        """
        Serialize a queryset with a nested serializer and check the result
        """
        model_instance_1 = ModelForTest.objects.create(thing_id=2004)
        model_instance_2 = ModelForTest.objects.create(thing_id=2005)
        obj = ParentModelForTest.objects.create(test_instance=model_instance_1)
        obj.test_instances.add(model_instance_2)
        ParentModelForTest.objects.create(test_instance=model_instance_2)
        query = ParentModelForTest.objects.all()
        serializer = ParentWithManyTestSerializer(query)
        expected = [
            {'id': 1,
             'test_instances': [
                 {'id': 2, 'thing': {'id': 2005, 'name': 'Name of the thing'}}
             ]},
            {'id': 2, 'test_instances': []}
        ]

        with mock.patch.dict('rest_client.client.ENDPOINTS', self.endpoints):
            result = serializer.data

        self.assertDictEqual(result[0], expected[0])
        self.assertDictEqual(result[1], expected[1])
