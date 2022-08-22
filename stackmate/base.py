"""
Provides base classes
"""
# -*- coding: utf-8 -*-
import operator
from pydoc import locate
from functools import reduce
from collections import OrderedDict
from stackmate.helpers import reduce_bool_list
from stackmate.exceptions import ValidationError

class AttributeDict(OrderedDict):
    """
    A class to convert a nested Dictionary into an object with key-values
    that are accessible using attribute notation (AttrDict.attribute) instead of
    key notation (Dict["key"]). This class recursively sets Dicts to objects,
    allowing you to recurse down nested dicts (like: AttrDict.attr.attr)
    """
    __slots__ = () # helps with memory usage

    # Inspired by:
    # http://stackoverflow.com/a/14620633/1551810
    # https://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute
    # http://databio.org/posts/python_AttributeDict.html
    # https://stackoverflow.com/questions/3387691/how-to-perfectly-override-a-dict
    def __init__(self, iterable, **kwargs):
        super().__init__(iterable, **kwargs)
        self._set_iterable(iterable)

    def get_path(self, path, default=None):
        """Returns a path in the state"""
        result = default

        try:
            result = reduce(operator.getitem, path.split('.'), self.__dict__)
        except KeyError:
            result = default
        except TypeError:
            result = default

        return result

    def set_path(self, path, contents):
        """Updates a part of the state for a given path"""
        if not path:
            raise ValueError('The path to update should not be empty')

        current_dict = self
        parts = path.split('.')

        for part in parts[:-1]:
            if part not in current_dict:
                current_dict[part] = {}

            current_dict = current_dict[part]

        current_dict[parts[-1]] = contents

        self._set_iterable(current_dict)

        return self

    def _set_iterable(self, iterable):
        """Sets the dictionary values"""
        for key, value in iterable.items():
            if isinstance(value, dict):
                self.__dict__[key] = AttributeDict(value)
            elif isinstance(value, list):
                self.__dict__[key] = [
                    AttributeDict(v) for v in value if isinstance(v, dict)
                ]
            else:
                self.__dict__[key] = value

        return self.__dict__

    def copy(self):
        """Copies the current attribute dict"""
        return AttributeDict(dict(self).copy())


class ModelAttribute:
    # pylint: disable=too-many-instance-attributes
    """Represents each attribute in a model"""
    updatable_options = ['required', 'datatype', 'shape', 'choices']

    def __init__(self, required=False, datatype=str, default=None, **kwargs):
        self.required = required
        self.datatype = locate(datatype) if isinstance(datatype, str) else datatype
        self.default = default
        self.shape = kwargs.get('shape')
        self.choices = kwargs.get('choices')
        self.name = kwargs.get('name')
        self.serializable = kwargs.get('serializable', True)
        self._validations = []

        self.setup_validations()

    def set_params(self, **options):
        """
        Sets the attribute's params
        """
        for name, opt in options.items():
            if name not in self.updatable_options:
                continue

            setattr(self, name, opt)

        # Reset the validations
        self.setup_validations()

    def setup_validations(self):
        """
        Creates the set of validation rules to be used when validating a ModelAttribute
        """
        self._validations = []

        if self.required:
            self._validations.append(self.validates_presence)

        if self.datatype:
            self._validations.append(
                lambda x: self.validates_datatype(x, self.datatype))

        if self.shape:
            if isinstance(self.datatype, dict):
                self._validations.append(
                    lambda x, shape=self.shape: self.validates_shape(x, shape))
            elif isinstance(self.datatype, list):
                self._validations.append(
                    lambda x, shape=self.shape: self.validates_list_of_shapes(x, shape))

        if self.choices:
            self._validations.append(
                lambda x, choices=self.choices: self.validates_inclusion(x, choices))

    @staticmethod
    def validates_presence(subject):
        """Validates a variable being present"""
        return bool(subject) is True

    @staticmethod
    def validates_datatype(subject, datatype):
        """Validates a variable being boolean"""
        return isinstance(subject, datatype)

    @staticmethod
    def validates_inclusion(subject, choices):
        """Validates whether the value is within a range of choices"""
        return subject in choices

    @staticmethod
    def validates_shape(subject, shape):
        """
        Shape validation
        """
        if not isinstance(subject, dict):
            raise ValueError('The subject should be a dictionary')

        if not isinstance(shape, dict):
            raise ValueError('The shape should be a dictionary')

        res = []

        for att, rules in shape.items():
            res.append(ModelAttribute.run_validations(subject[att], rules))

        return reduce_bool_list(res)

    @staticmethod
    def validates_list_of_shapes(subject, shape):
        """
        Validates a list whose all members should comply with a specific shape
        """
        if not isinstance(subject, list):
            raise ValueError('The subject should be a list')

        if not isinstance(shape, dict):
            raise ValueError('The shape should be a dictionary')

        if not all(isinstance(x, dict) for x in subject):
            raise ValueError('All items in the subject should be dictionaries')

        results = [ModelAttribute.validates_shape(x, shape) for x in subject]
        return reduce_bool_list(results)

    @staticmethod
    def run_validations(subject, rules):
        """
        Runs a validation
        """
        results = []
        rules = rules if isinstance(rules, list) else [rules]

        for rule in rules:
            if not callable(rule):
                raise AttributeError(
                    'Invalid validation rule of type {tp}. Should be callable'.format(
                        tp=type(rule)))

            # evaluate the validation
            results.append(rule(subject))

        return reduce_bool_list(results)

    @property
    def validations(self):
        """Returns the list of validations that have been set up"""
        return self._validations

    def validate(self, value):
        """
        Validates a specific value for an attribute
        """
        if not self.required and not value:
            return True

        results = [ModelAttribute.run_validations(value, rules) for rules in self.validations]
        return reduce_bool_list(results)

    def __dict__(self):
        return {
            'name': self.name,
            'datatype': self.datatype.__class__.__name__,
            'default': self.default,
            'choices': self.choices,
            'shape': self.shape,
        }


class Model:
    """
    Provides support to dynamically load attributes via a YML configuration
    """
    def __init__(self, **kwargs):
        self._attributes = {}
        self.__values = {}
        self.setup_attributes(additional_setup=kwargs.get('model_setup', {}))
        self.errors = {}
        self.attributes = kwargs
        self.serializable_attributes = [
            name for name, att in self._attributes.items() if att.serializable
        ]

    def setup_attributes(self, additional_setup=None):
        """
        Initialize the attributes for the model
        """
        attributes = {}
        for name in dir(self.__class__):
            att = getattr(self.__class__, name)

            if isinstance(att, ModelAttribute):
                attr_name = name[1:]
                attributes[attr_name] = att

        if not isinstance(additional_setup, dict):
            raise ValueError(
                'Expected a dictionary mapping { name => ModelAttribute(...), ... } for model_setup'
            )

        attributes.update(additional_setup)

        for name, att in attributes.items():
            if not isinstance(att, ModelAttribute):
                raise ValueError('Attribute` {n} is not a valid ModelAttribute instance', n=name)

            # hold the ModelAttribute instance in a separate _attributes dictionary
            self._attributes[name] = att
            # assign the attribute's name to the ModelAttribute instance
            att.name = name
            # setup the instance variable
            setattr(self, name, att.default)

    # This is just to make the linter happy
    def __getattribute__(self, name): # pylint: disable=useless-super-delegation
        return super().__getattribute__(name)

    @property
    def attribute_names(self):
        """Returns the attribute names"""
        return list(self._attributes.keys())

    @property
    def attributes(self):
        """
        Returns the model's attributes
        """
        return {name: getattr(self, name) for name in self.attribute_names}

    @attributes.setter
    def attributes(self, values):
        for name, value in values.items():
            self.set_attribute(name, value)

    def set_attribute(self, name, value):
        """Sets an attribute value"""
        if name in self.attribute_names and value is not None:
            setattr(self, name, value)

    def set_attribute_params(self, attr, **params):
        """
        Updates an attribute's params such as
        - whether the attribute is required
        - choices to choose from etc
        """
        if attr not in self.attribute_names:
            raise AttributeError('Attribute {at} in model {m} was not found'.format(
                at=attr, m=self.__class__.__name__))

        self._attributes[attr].set_params(**params)

    def validate(self):
        """
        Validate the model
        """
        for name, attr in self._attributes.items():
            value = getattr(self, name)

            if not attr.validate(value):
                self.errors[name] = 'Attribute `{at}` in model {m} is invalid'.format(
                    at=name, m=self.__class__.__name__)

        if self.errors:
            raise ValidationError(self.errors)

        return self.post_validate()

    def post_validate(self):
        # pylint: disable=R0201
        """Allows to run additional validations after the main model is validated"""
        return True

    def serialize(self):
        """Serializes a model"""
        serialized = {}

        for name in self.serializable_attributes:
            attr = self.attributes[name]

            if isinstance(attr, Model):
                serialized[name] = attr.serialize()
            elif isinstance(attr, list) and all([isinstance(m, Model) for m in attr]):
                serialized[name] = [m.serialize() for m in attr]
            elif isinstance(attr, dict) and all([isinstance(m, Model) for m in attr.values()]):
                serialized[name] = {k: m.serialize() for k, m in attr.items()}
            else:
                serialized[name] = attr

        return serialized

    def __dict__(self):
        return self.serialize()
