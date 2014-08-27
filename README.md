django-remote-field
===================

A field from a remote resource to be included in a DRF serializer.

This app includes a serializer mixin adding the functionality to retrieve
fields from external remote servers.

It relies on the final serializer to include some RemoteFields telling
which fields need to be retrieved from which service.

The complete serializer should look like the following example:

    class MySerializer(RemoteFieldsModelSerializerMixin,
                       serializers.ModerlSerializer):

        thing = RemoteField(
            source='thing_id', remote_sources=('id', 'name',)
            endpoints={
                'list': client.some.endpoint_list,
                'detail': client.some.endpoint_detail
            }
        )

        class Meta:
            Model = MyModel
            fields = ('id', 'my_local_field', 'thing')

Where each endpoint is expressed using the `rest_client` library.
More info: https://github.com/rockabox/rest_client_builder


You can also define a nested structure of serializers containing RemoteFields:

    class ParentTestSerializer(RemoteFieldsModelSerializerMixin,
                               serializers.ModelSerializer):
        test_instances = MySerializer(many=True)

        class Meta:
            model = ParentModelForTest
            fields = ('id', 'test_instances')
