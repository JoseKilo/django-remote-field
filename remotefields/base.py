from rest_framework.fields import WritableField
from rest_framework.serializers import is_simple_callable


class RemoteField(WritableField):
    """
    Custom field to be included within a serializer extending
    RemoteFieldsModelSerializerMixin (check below). It is used only to store
    information about which fields must be retrieved from remote services.

        thing = RemoteField(
            source='thing_id', remote_sources=('id', 'name',)
            endpoints={
                'list': client.some.endpoint_list,
                'detail': client.some.endpoint_detail
            }
        )
    """

    endpoints = None
    remote_sources = None
    flat = False

    def __init__(self, endpoints, remote_sources,
                 flat=False, *args, **kwargs):
        """
        :param args: Standard DRF arguments
        :param kwargs: Standard DRF arguments. It will contain 'source':
                       the source of data to fill the field
        :param endpoints: Dictionary containing 'list' and 'detail' endpoints
        :param remote_sources: Field names to retrieve from the remote service
        :param flat: Boolean indicating if it is a flat or nested structure
        """
        if flat and len(remote_sources) > 1:
            raise ValueError('Flat fields can only specify a remote_source')

        self.endpoints = endpoints
        self.remote_sources = remote_sources
        self.flat = flat
        super(RemoteField, self).__init__(*args, **kwargs)

    def field_to_native(self, obj, field_name):
        """
        The serializer class will fill this field content later
        """
        return getattr(obj, self.source, None)


class RemoteFieldsModelSerializerMixin(object):
    """
    Custom serializer mixin adding the functionality to retrieve fields from
    external remote servers.

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

    Where each endpoint is expressed using the rest_client library.
    More info: https://github.com/rockabox/rest_client_builder
    """

    def to_native(self, obj):
        """
        Serialize objects -> primitives.
        """
        if is_simple_callable(getattr(obj, 'all', None)):
            ret = [super(RemoteFieldsModelSerializerMixin, self).to_native(i)
                   for i in obj.all()]
        else:
            ret = super(RemoteFieldsModelSerializerMixin, self).to_native(obj)

        for field_name, field in self.get_remote_serializers():
            obj_field = getattr(obj, field_name, None)
            ret[field_name] = field.__class__(obj_field).data

        return ret

    @property
    def data(self):
        """
        Returns the serialized data on the serializer.
        """
        existing_fields = self.opts.fields
        remote_fields_sources = [f.source for _, f in self.get_remote_fields()]
        new_sources = set(remote_fields_sources) - set(existing_fields)
        self.opts.fields += tuple(new_sources)
        self.fields = self.get_fields()

        self._data = super(RemoteFieldsModelSerializerMixin, self).data

        self.opts.fields = tuple(set(self.fields) - new_sources)
        self.fields = self.get_fields()

        if isinstance(self._data, list):
            self._data = self._add_remote_fields_to_list(self._data)
            for instance in self._data:
                for field in new_sources:
                    del instance[field]
        else:
            self._data = self._add_remote_fields_to_obj(self._data)
            for field in new_sources:
                del self._data[field]
        return self._data

    def get_remote_fields(self):
        all_fields = self.get_fields()
        return [(field_name, field) for field_name, field in all_fields.items()
                if isinstance(field, RemoteField)]

    def get_remote_serializers(self):
        all_fields = self.get_fields()
        return [(field_name, field) for field_name, field in all_fields.items()
                if isinstance(field, RemoteFieldsModelSerializerMixin)]

    def _add_remote_fields_to_list(self, data):
        """
        Add every remote field data to every object in a list.

            - If the pk to retrieve remote data does not exist,
              the resulting field be null.
        """
        for local_field_name, remote_field in self.get_remote_fields():
            list_endpoint = remote_field.endpoints['list']
            remote_objects = list_endpoint()

            # We use a dict to speed the access to the set of remote_objects
            remote_objects_data = dict()
            for remote_object in remote_objects:
                pk = remote_object['id']
                remote_objects_data[pk] = remote_object

            for local_object in self._data:
                remote_pk = local_object[remote_field.source]
                try:
                    remote_object = remote_objects_data[remote_pk]

                    local_object[local_field_name] = self._fill_remote_field(
                        remote_field, remote_object)
                except KeyError:
                    local_object[local_field_name] = None
        return data

    def _add_remote_fields_to_obj(self, data):
        """
        Add every remote field data to an object.

            - If a field is already expanded for the given object,
              it will be ignored.
            - If the pk to retrieve remote data does not exist,
              the resulting field be null.
        """
        for local_field_name, remote_field in self.get_remote_fields():
            detail_endpoint = remote_field.endpoints['detail']

            if (local_field_name in data and
                    isinstance(data[remote_field.source], dict)):
                data[local_field_name] = data[remote_field.source]
                continue

            try:
                pk = data[remote_field.source]
                if pk is None:
                    data[local_field_name] = None
                else:
                    remote_object = detail_endpoint(pk=pk)

                    data[local_field_name] = self._fill_remote_field(
                        remote_field, remote_object)

            except (KeyError, ValueError):
                data[local_field_name] = None
        return data

    def _fill_remote_field(self, remote_field, remote_object):
        if remote_field.flat:
            field_name = remote_field.remote_sources[0]
            return remote_object[field_name]

        remote_object_fields = {}
        for field_name in remote_field.remote_sources:
            remote_field_value = remote_object[field_name]
            remote_object_fields[field_name] = remote_field_value
        return remote_object_fields
