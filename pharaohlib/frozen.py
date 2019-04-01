from inspect import signature, Parameter
from itertools import chain
from functools import update_wrapper


class Frozen:
    """
    A base class to allow for easy copying of simple types
    NOTE: this should only be used with immutable types
    """

    def __new__(cls, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], cls):
            return args[0].replace(**kwargs)
        ret = super().__new__(cls)
        ret.__args = (args, kwargs)
        ret.__repr = None
        ret.__hash = None
        return ret

    def replace(self, **changes):
        """
        create a new object of the type of self, using self's arguments as template
        :param changes: initialization arguments to change
        :return: a new instance of self's type, using a mix of self's init arguments and kwargs
        """
        if not changes:
            return self

        args = list(self.__args[0])
        kwargs = dict(self.__args[1])
        for k, v in changes.items():
            param_index = self.__new_params.get(k, -1)
            if 0 <= param_index < len(args):
                args[param_index] = v
            else:
                kwargs[k] = v
        return type(self)(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        # to allow kwargs->args replacement, we need a dict of all of the class's original positional arguments
        super().__init_subclass__(**kwargs)
        update_wrapper(cls.replace, cls.__new__)
        try:
            parent_params = cls.__new_params
        except AttributeError:
            parent_params = {}

        cls.__new_params = {}
        for i, p in enumerate(signature(cls.__new__).parameters.values()):
            if p.kind == Parameter.VAR_POSITIONAL:
                for n, j in parent_params.items():
                    cls.__new_params[n] = j + i

            if p.kind not in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY):
                break

            cls.__new_params[p.name] = i

    def __getnewargs_ex__(self):
        return self.__args

    # all the other methods here are rudimentary but they're useful to have
    def __repr__(self):
        if self.__repr is None:
            args = chain(
                (repr(a) for a in self.__args[0]),
                (str(k) + ' = ' + repr(v) for k, v in self.__args[1].items())
            )
            self.__repr = type(self).__name__ + '(' + ', '.join(args) + ')'
        return self.__repr

    def __eq__(self, other):
        return super().__eq__(self, other) or (isinstance(other, type(self))
                                               and self.__args == other.__args)

    def __hash__(self):
        if self.__hash is None:
            self.__hash = hash(
                (type(self),
                 self.__args[0],
                 tuple(sorted(self.__args[1].items(), key=lambda x: hash(x[0]))))
            )
        return self.__hash
