"""Provides tests for dependencies"""
# -*- coding: utf-8 -*-
# pylint: disable=E1101,C0111,W0612,R0915
import pytest
from stackmate.base import AttributeDict
from stackmate.base import Model, ModelAttribute
from stackmate.exceptions import ValidationError

class InnerFakeModel(Model):
    _inner1 = ModelAttribute(required=True, datatype=int, default=1)
    _inner2 = ModelAttribute(required=True)

    def __init__(self, **kwargs):
        self._inner2 = None
        super().__init__(**kwargs)

    @property
    def inner2(self):
        return self._inner2

    @inner2.setter
    def inner2(self, attrs):
        if attrs:
            self._inner2 = InnerFakeModel(**attrs)


class FakeModel(Model):
    """
    Fake model to test out the base model class
    """
    _attr1 = ModelAttribute(required=True, datatype=bool)
    _attr2 = ModelAttribute(required=True)
    _attr3 = ModelAttribute(required=True, datatype=list)

    def __init__(self, **kwargs):
        self._attr3 = None
        super().__init__(**kwargs)

    @property
    def attr3(self):
        return self._attr3

    @attr3.setter
    def attr3(self, attrs):
        if attrs:
            self._attr3 = InnerFakeModel(**attrs)


DICTIONARY = {
    'test': 100,
    'mytest': 200,
    'nested': {
        'inner': 300,
    },
    'empty': {},
    'somewhere': {
        'far': {
            'beyond': True,
        },
    },
}


def describe_attribute_dict():
    def it_can_access_property_by_using_dot_notation():
        attr_dict = AttributeDict(DICTIONARY)
        assert isinstance(attr_dict, AttributeDict)
        assert hasattr(attr_dict, 'test')
        assert attr_dict.test == DICTIONARY['test']
        assert attr_dict.nested.inner == DICTIONARY['nested']['inner']

    def it_returns_a_path_in_the_dict():
        attr_dict = AttributeDict(DICTIONARY)
        assert attr_dict.get_path('somewhere.far.beyond') is True
        assert attr_dict.get_path('somewhere.beyond.the.moon') is None

    def it_updates_a_root_path_in_the_dict():
        attr_dict = AttributeDict(DICTIONARY)
        assert attr_dict.get_path('awesomeness') is None
        attr_dict.set_path('awesomeness', 1000)
        assert attr_dict.get_path('awesomeness') == 1000

    def it_updates_a_path_in_the_dict():
        attr_dict = AttributeDict(DICTIONARY)
        assert attr_dict.get_path('empty') == {}
        assert attr_dict.get_path('empty.not_empty_anymore') is None
        updated = attr_dict.set_path('empty', {'not_empty_anymore': 12345})
        # make sure the instance itself got updated
        assert updated == attr_dict
        assert attr_dict.get_path('empty.not_empty_anymore') == 12345

def describe_model_attribute():
    def it_initializes_correctly():
        attr = ModelAttribute()
        # check default values
        assert isinstance(attr.required, bool)
        assert attr.datatype is str
        assert attr.default is None
        assert attr.shape is None
        assert attr.name is None

    def it_validates_presence():
        assert ModelAttribute.validates_presence(5) is True
        assert ModelAttribute.validates_presence('abc') is True
        assert ModelAttribute.validates_presence(None) is False
        assert ModelAttribute.validates_presence(False) is False

    def it_validates_datatype():
        assert ModelAttribute.validates_datatype(5, int) is True
        assert ModelAttribute.validates_datatype('abc', str) is True
        assert ModelAttribute.validates_datatype({}, dict) is True
        assert ModelAttribute.validates_datatype([], list) is True
        assert ModelAttribute.validates_datatype(5, str) is False
        assert ModelAttribute.validates_datatype('abc', dict) is False

    def it_validates_inclusion():
        assert ModelAttribute.validates_inclusion(1, [1, 2, 3]) is True
        assert ModelAttribute.validates_inclusion(5, [1, 2, 3]) is False

    def it_validates_shape():
        shape = {
            'attr1': [
                ModelAttribute.validates_presence,
                lambda x: ModelAttribute.validates_datatype(x, int),
            ],
            'attr2': [
                ModelAttribute.validates_presence,
            ],
        }

        assert ModelAttribute.validates_shape({'attr1': 5, 'attr2': 'abc'}, shape=shape) is True
        assert ModelAttribute.validates_shape({'attr1': None, 'attr2': None}, shape=shape) is False

    def it_validates_list_of_shapes():
        shape = {
            'attr1': [
                ModelAttribute.validates_presence,
                lambda x: ModelAttribute.validates_datatype(x, int),
            ],
            'attr2': [
                ModelAttribute.validates_presence,
            ],
        }

        subject1 = [
            {'attr1': 5, 'attr2': 'abc'},
            {'attr1': 6, 'attr2': 'def'},
        ]

        subject2 = [
            {'attr1': None, 'attr2': None},
        ]

        assert ModelAttribute.validates_list_of_shapes(subject1, shape=shape) is True
        assert ModelAttribute.validates_list_of_shapes(subject2, shape=shape) is False


def describe_model():
    def initializes_the_model_properly():
        model = FakeModel()
        assert isinstance(model, FakeModel) is True
        assert isinstance(model, Model) is True
        assert hasattr(model, 'attr1') is True
        assert hasattr(model, 'attr2') is True

    def it_assigns_the_attributes_properly():
        model = FakeModel()
        attrs = {'attr1': 5, 'attr2': 'abc'}
        model.attributes = attrs

        assert model.attr1 == attrs['attr1']
        assert model.attr2 == attrs['attr2']
        assert model.attr3 is None

    def it_returns_the_attributes_properly():
        attrs = {'attr1': 5, 'attr2': 'abc', 'attr3': None}
        model = FakeModel(**attrs)
        assert isinstance(model.attributes, dict)
        assert model.attributes.get('attr1') == attrs['attr1']
        assert model.attributes.get('attr2') == attrs['attr2']
        assert model.attributes.get('attr3') is None

        assert list(attrs.keys()) == list(model.attribute_names)
        assert attrs == model.attributes

    def it_assigns_the_default_values():
        model = FakeModel()
        assert model.attr1 is None
        assert model.attr2 is None

    def it_initializes_with_attribute_names_and_ignores_missing_attributes():
        model = FakeModel(attr1=5, attr2=10, someother=12345)
        assert model.attr1 == 5
        assert model.attr2 == 10
        assert hasattr(model, 'someother') is False

    def it_validates_the_attributes():
        model = FakeModel()

        with pytest.raises(ValidationError) as err:
            model.validate()

    def it_serializes_the_model():
        attributes = {
            'attr1': 10,
            'attr2': 20,
            'attr3': {
                'inner1': 30,
                'inner2': {
                    'inner1': 40,
                    'inner2': {
                        'inner1': 50,
                        'inner2': None,
                    },
                },
            },
        }

        model = FakeModel(**attributes)
        serialized = model.serialize()
        assert isinstance(serialized, dict)
        assert serialized == attributes
