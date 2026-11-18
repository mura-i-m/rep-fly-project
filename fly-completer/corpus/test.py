import re
import sys
import copy
import types
import inspect
import keyword
import itertools
import abc
from reprlib import recursive_repr
__all__ =['dataclass',
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
]
class FrozenInstanceError (AttributeError ):pass
class _HAS_DEFAULT_FACTORY_CLASS :
    def __repr__ (self ):
        return '<factory>'
_HAS_DEFAULT_FACTORY =_HAS_DEFAULT_FACTORY_CLASS ()
class _MISSING_TYPE :
    pass
MISSING =_MISSING_TYPE ()
class _KW_ONLY_TYPE :
    pass
KW_ONLY =_KW_ONLY_TYPE ()
_EMPTY_METADATA =types .MappingProxyType ({})
class _FIELD_BASE :
    def __init__ (self ,name ):
        self .name =name
    def __repr__ (self ):
        return self .name
_FIELD =_FIELD_BASE ('_FIELD')
_FIELD_CLASSVAR =_FIELD_BASE ('_FIELD_CLASSVAR')
_FIELD_INITVAR =_FIELD_BASE ('_FIELD_INITVAR')
_FIELDS ='__dataclass_fields__'
_PARAMS ='__dataclass_params__'
_POST_INIT_NAME ='__post_init__'
_MODULE_IDENTIFIER_RE =re .compile (r'^(?:\s*(\w+)\s*\.)?\s*(\w+)')
_ATOMIC_TYPES =frozenset ({
types .NoneType ,
bool ,
int ,
float ,
str ,
complex ,
bytes ,
types .EllipsisType ,
types .NotImplementedType ,
types .CodeType ,
types .BuiltinFunctionType ,
types .FunctionType ,
type ,
range ,
property ,
})
class InitVar :
    __slots__ =('type',)
    def __init__ (self ,type ):
        self .type =type
    def __repr__ (self ):
        if isinstance (self .type ,type ):
            type_name =self .type .__name__
        else :
            type_name =repr (self .type )
        return f'dataclasses.InitVar[{type_name }]'
    def __class_getitem__ (cls ,type ):
        return InitVar (type )
class Field :
    __slots__ =('name',
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    )
    def __init__ (self ,default ,default_factory ,init ,repr ,hash ,compare ,
    metadata ,kw_only ):
        self .name =None
        self .type =None
        self .default =default
        self .default_factory =default_factory
        self .init =init
        self .repr =repr
        self .hash =hash
        self .compare =compare
        self .metadata =(_EMPTY_METADATA
        if metadata is None else
        types .MappingProxyType (metadata ))
        self .kw_only =kw_only
        self ._field_type =None
    @recursive_repr ()
    def __repr__ (self ):
        return ('Field('
        f'name={self .name !r },'
        f'type={self .type !r },'
        f'default={self .default !r },'
        f'default_factory={self .default_factory !r },'
        f'init={self .init !r },'
        f'repr={self .repr !r },'
        f'hash={self .hash !r },'
        f'compare={self .compare !r },'
        f'metadata={self .metadata !r },'
        f'kw_only={self .kw_only !r },'
        f'_field_type={self ._field_type }'
        "")
    def __set_name__ (self ,owner ,name ):
        func =getattr (type (self .default ),'__set_name__',None )
        if func :
            func (self .default ,owner ,name )
    __class_getitem__ =classmethod (types .GenericAlias )
class _DataclassParams :
    __slots__ =('init',
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    )
    def __init__ (self ,
    init ,repr ,eq ,order ,unsafe_hash ,frozen ,
    match_args ,kw_only ,slots ,weakref_slot ):
        self .init =init
        self .repr =repr
        self .eq =eq
        self .order =order
        self .unsafe_hash =unsafe_hash
        self .frozen =frozen
        self .match_args =match_args
        self .kw_only =kw_only
        self .slots =slots
        self .weakref_slot =weakref_slot
    def __repr__ (self ):
        return ('_DataclassParams('
        f'init={self .init !r },'
        f'repr={self .repr !r },'
        f'eq={self .eq !r },'
        f'order={self .order !r },'
        f'unsafe_hash={self .unsafe_hash !r },'
        f'frozen={self .frozen !r },'
        f'match_args={self .match_args !r },'
        f'kw_only={self .kw_only !r },'
        f'slots={self .slots !r },'
        f'weakref_slot={self .weakref_slot !r }'
        "")
def field (*,default =MISSING ,default_factory =MISSING ,init =True ,repr =True ,
hash =None ,compare =True ,metadata =None ,kw_only =MISSING ):
    if default is not MISSING and default_factory is not MISSING :
        raise ValueError ('cannot specify both default and default_factory')
    return Field (default ,default_factory ,init ,repr ,hash ,compare ,
    metadata ,kw_only )
def _fields_in_init_order (fields ):
    return (tuple (f for f in fields if f .init and not f .kw_only ),
    tuple (f for f in fields if f .init and f .kw_only )
    )
def _tuple_str (obj_name ,fields ):
    if not fields :
        return '()'
    return f'({",".join ([f"{obj_name }.{f .name }"for f in fields ])},)'
class _FuncBuilder :
    def __init__ (self ,globals ):
        self .names =[]
        self .src =[]
        self .globals =globals
        self .locals ={}
        self .overwrite_errors ={}
        self .unconditional_adds ={}
    def add_fn (self ,name ,args ,body ,*,locals =None ,return_type =MISSING ,
    overwrite_error =False ,unconditional_add =False ,decorator =None ):
        if locals is not None :
            self .locals .update (locals )
        if overwrite_error :
            self .overwrite_errors [name ]=overwrite_error
        if unconditional_add :
            self .unconditional_adds [name ]=True
        self .names .append (name )
        if return_type is not MISSING :
            self .locals [f'__dataclass_{name }_return_type__']=return_type
            return_annotation =f'->__dataclass_{name }_return_type__'
        else :
            return_annotation =''
        args =','.join (args )
        body ='\n'.join (body )
        self .src .append (f'{f' {decorator }\n'if decorator else ''} def {name }({args }){return_annotation }:\n{body }')
    def add_fns_to_class (self ,cls ):
        fns_src ='\n'.join (self .src )
        local_vars =','.join (self .locals .keys ())
        if len (self .names )==0 :
            return_names ='()'
        else :
            return_names =f'({",".join (self .names )},)'
        txt =f"def __create_fn__({local_vars }):\n{fns_src }\n return {return_names }"
        ns ={}
        exec (txt ,self .globals ,ns )
        fns =ns ['__create_fn__'](**self .locals )
        for name ,fn in zip (self .names ,fns ):
            fn .__qualname__ =f"{cls .__qualname__ }.{fn .__name__ }"
            if self .unconditional_adds .get (name ,False ):
                setattr (cls ,name ,fn )
            else :
                already_exists =_set_new_attribute (cls ,name ,fn )
                if already_exists and (msg_extra :=self .overwrite_errors .get (name )):
                    error_msg =(f'Cannot overwrite attribute {fn .__name__ } '
                    f'in class {cls .__name__ }')
                    if not msg_extra is True :
                        error_msg =f'{error_msg } {msg_extra }'
                    raise TypeError (error_msg )
def _field_assign (frozen ,name ,value ,self_name ):
    if frozen :
        return f'  __dataclass_builtins_object__.__setattr__({self_name },{name !r },{value })'
    return f'  {self_name }.{name }={value }'
def _field_init (f ,frozen ,globals ,self_name ,slots ):
    default_name =f'__dataclass_dflt_{f .name }__'
    if f .default_factory is not MISSING :
        if f .init :
            globals [default_name ]=f .default_factory
            value =(f'{default_name }() '
            f'if {f .name } is __dataclass_HAS_DEFAULT_FACTORY__ '
            f'else {f .name }')
        else :
            globals [default_name ]=f .default_factory
            value =f'{default_name }()'
    else :
        if f .init :
            if f .default is MISSING :
                value =f .name
            elif f .default is not MISSING :
                globals [default_name ]=f .default
                value =f .name
        else :
            if slots and f .default is not MISSING :
                globals [default_name ]=f .default
                value =default_name
            else :
                return None
    if f ._field_type is _FIELD_INITVAR :
        return None
    return _field_assign (frozen ,f .name ,value ,self_name )
def _init_param (f ):
    if f .default is MISSING and f .default_factory is MISSING :
        default =''
    elif f .default is not MISSING :
        default =f'=__dataclass_dflt_{f .name }__'
    elif f .default_factory is not MISSING :
        default ='=__dataclass_HAS_DEFAULT_FACTORY__'
    return f'{f .name }:__dataclass_type_{f .name }__{default }'
def _init_fn (fields ,std_fields ,kw_only_fields ,frozen ,has_post_init ,
self_name ,func_builder ,slots ):
    seen_default =None
    for f in std_fields :
        if f .init :
            if not (f .default is MISSING and f .default_factory is MISSING ):
                seen_default =f
            elif seen_default :
                raise TypeError (f'non-default argument {f .name !r } '
                f'follows default argument {seen_default .name !r }')
    locals ={**{f'__dataclass_type_{f .name }__':f .type for f in fields },
    **{'__dataclass_HAS_DEFAULT_FACTORY__':_HAS_DEFAULT_FACTORY ,
    "":object ,
    }
    }
    body_lines =[]
    for f in fields :
        line =_field_init (f ,frozen ,locals ,self_name ,slots )
        if line :
            body_lines .append (line )
    if has_post_init :
        params_str =','.join (f .name for f in fields
        if f ._field_type is _FIELD_INITVAR )
        body_lines .append (f'  {self_name }.{_POST_INIT_NAME }({params_str })')
    if not body_lines :
        body_lines =['  pass']
    _init_params =[_init_param (f )for f in std_fields ]
    if kw_only_fields :
        _init_params +=['*']
        _init_params +=[_init_param (f )for f in kw_only_fields ]
    func_builder .add_fn ('__init__',
    [self_name ]+_init_params ,
    body_lines ,
    locals =locals ,
    return_type =None )
def _frozen_set_del_attr (cls ,fields ,func_builder ):
    locals ={'__class__':cls ,
    "":FrozenInstanceError }
    condition ='type(self) is __class__'
    if fields :
        condition +=' or name in {'+', '.join (repr (f .name )for f in fields )+'}'
    func_builder .add_fn ('__setattr__',
    ('self','name','value'),
    (f'  if {condition }:',
    "",
    f'  super(__class__, self).__setattr__(name, value)'),
    locals =locals ,
    overwrite_error =True )
    func_builder .add_fn ('__delattr__',
    ('self','name'),
    (f'  if {condition }:',
    "",
    f'  super(__class__, self).__delattr__(name)'),
    locals =locals ,
    overwrite_error =True )
def _is_classvar (a_type ,typing ):
    return (a_type is typing .ClassVar
    or (type (a_type )is typing ._GenericAlias
    and a_type .__origin__ is typing .ClassVar ))
def _is_initvar (a_type ,dataclasses ):
    return (a_type is dataclasses .InitVar
    or type (a_type )is dataclasses .InitVar )
def _is_kw_only (a_type ,dataclasses ):
    return a_type is dataclasses .KW_ONLY
def _is_type (annotation ,cls ,a_module ,a_type ,is_type_predicate ):
    match =_MODULE_IDENTIFIER_RE .match (annotation )
    if match :
        ns =None
        module_name =match .group (1 )
        if not module_name :
            ns =sys .modules .get (cls .__module__ ).__dict__
        else :
            module =sys .modules .get (cls .__module__ )
            if module and module .__dict__ .get (module_name )is a_module :
                ns =sys .modules .get (a_type .__module__ ).__dict__
        if ns and is_type_predicate (ns .get (match .group (2 )),a_module ):
            return True
    return False
def _get_field (cls ,a_name ,a_type ,default_kw_only ):
    default =getattr (cls ,a_name ,MISSING )
    if isinstance (default ,Field ):
        f =default
    else :
        if isinstance (default ,types .MemberDescriptorType ):
            default =MISSING
        f =field (default =default )
    f .name =a_name
    f .type =a_type
    f ._field_type =_FIELD
    typing =sys .modules .get ('typing')
    if typing :
        if (_is_classvar (a_type ,typing )
        or (isinstance (f .type ,str )
        and _is_type (f .type ,cls ,typing ,typing .ClassVar ,
        _is_classvar ))):
            f ._field_type =_FIELD_CLASSVAR
    if f ._field_type is _FIELD :
        dataclasses =sys .modules [__name__ ]
        if (_is_initvar (a_type ,dataclasses )
        or (isinstance (f .type ,str )
        and _is_type (f .type ,cls ,dataclasses ,dataclasses .InitVar ,
        _is_initvar ))):
            f ._field_type =_FIELD_INITVAR
    if f ._field_type in (_FIELD_CLASSVAR ,_FIELD_INITVAR ):
        if f .default_factory is not MISSING :
            raise TypeError (f'field {f .name } cannot have a '
            "")
    if f ._field_type in (_FIELD ,_FIELD_INITVAR ):
        if f .kw_only is MISSING :
            f .kw_only =default_kw_only
    else :
        assert f ._field_type is _FIELD_CLASSVAR
        if f .kw_only is not MISSING :
            raise TypeError (f'field {f .name } is a ClassVar but specifies '
            "")
    if f ._field_type is _FIELD and f .default .__class__ .__hash__ is None :
        raise ValueError (f'mutable default {type (f .default )} for field '
        f'{f .name } is not allowed: use default_factory')
    return f
def _set_new_attribute (cls ,name ,value ):
    if name in cls .__dict__ :
        return True
    setattr (cls ,name ,value )
    return False
def _hash_set_none (cls ,fields ,func_builder ):
    cls .__hash__ =None
def _hash_add (cls ,fields ,func_builder ):
    flds =[f for f in fields if (f .compare if f .hash is None else f .hash )]
    self_tuple =_tuple_str ('self',flds )
    func_builder .add_fn ('__hash__',
    ('self',),
    [f'  return hash({self_tuple })'],
    unconditional_add =True )
def _hash_exception (cls ,fields ,func_builder ):
    raise TypeError (f'Cannot overwrite attribute __hash__ '
    f'in class {cls .__name__ }')
_hash_action ={(False ,False ,False ,False ):None ,
(False ,False ,False ,True ):None ,
(False ,False ,True ,False ):None ,
(False ,False ,True ,True ):None ,
(False ,True ,False ,False ):_hash_set_none ,
(False ,True ,False ,True ):None ,
(False ,True ,True ,False ):_hash_add ,
(False ,True ,True ,True ):None ,
(True ,False ,False ,False ):_hash_add ,
(True ,False ,False ,True ):_hash_exception ,
(True ,False ,True ,False ):_hash_add ,
(True ,False ,True ,True ):_hash_exception ,
(True ,True ,False ,False ):_hash_add ,
(True ,True ,False ,True ):_hash_exception ,
(True ,True ,True ,False ):_hash_add ,
(True ,True ,True ,True ):_hash_exception ,
}
def _process_class (cls ,init ,repr ,eq ,order ,unsafe_hash ,frozen ,
match_args ,kw_only ,slots ,weakref_slot ):
    fields ={}
    if cls .__module__ in sys .modules :
        globals =sys .modules [cls .__module__ ].__dict__
    else :
        globals ={}
    setattr (cls ,_PARAMS ,_DataclassParams (init ,repr ,eq ,order ,
    unsafe_hash ,frozen ,
    match_args ,kw_only ,
    slots ,weakref_slot ))
    any_frozen_base =False
    all_frozen_bases =None
    has_dataclass_bases =False
    for b in cls .__mro__ [-1 :0 :-1 ]:
        base_fields =getattr (b ,_FIELDS ,None )
        if base_fields is not None :
            has_dataclass_bases =True
            for f in base_fields .values ():
                fields [f .name ]=f
            if all_frozen_bases is None :
                all_frozen_bases =True
            current_frozen =getattr (b ,_PARAMS ).frozen
            all_frozen_bases =all_frozen_bases and current_frozen
            any_frozen_base =any_frozen_base or current_frozen
    cls_annotations =inspect .get_annotations (cls )
    cls_fields =[]
    KW_ONLY_seen =False
    dataclasses =sys .modules [__name__ ]
    for name ,type in cls_annotations .items ():
        if (_is_kw_only (type ,dataclasses )
        or (isinstance (type ,str )
        and _is_type (type ,cls ,dataclasses ,dataclasses .KW_ONLY ,
        _is_kw_only ))):
            if KW_ONLY_seen :
                raise TypeError (f'{name !r } is KW_ONLY, but KW_ONLY '
                "")
            KW_ONLY_seen =True
            kw_only =True
        else :
            cls_fields .append (_get_field (cls ,name ,type ,kw_only ))
    for f in cls_fields :
        fields [f .name ]=f
        if isinstance (getattr (cls ,f .name ,None ),Field ):
            if f .default is MISSING :
                delattr (cls ,f .name )
            else :
                setattr (cls ,f .name ,f .default )
    for name ,value in cls .__dict__ .items ():
        if isinstance (value ,Field )and not name in cls_annotations :
            raise TypeError (f'{name !r } is a field but has no type annotation')
    if has_dataclass_bases :
        if any_frozen_base and not frozen :
            raise TypeError ('cannot inherit non-frozen dataclass from a '
            "")
        if all_frozen_bases is False and frozen :
            raise TypeError ('cannot inherit frozen dataclass from a '
            "")
    setattr (cls ,_FIELDS ,fields )
    class_hash =cls .__dict__ .get ('__hash__',MISSING )
    has_explicit_hash =not (class_hash is MISSING or
    (class_hash is None and '__eq__'in cls .__dict__ ))
    if order and not eq :
        raise ValueError ('eq must be true if order is true')
    all_init_fields =[f for f in fields .values ()
    if f ._field_type in (_FIELD ,_FIELD_INITVAR )]
    (std_init_fields ,
    kw_only_init_fields )=_fields_in_init_order (all_init_fields )
    func_builder =_FuncBuilder (globals )
    if init :
        has_post_init =hasattr (cls ,_POST_INIT_NAME )
        _init_fn (all_init_fields ,
        std_init_fields ,
        kw_only_init_fields ,
        frozen ,
        has_post_init ,
        ""if 'self'in fields
        else 'self',
        func_builder ,
        slots ,
        )
    _set_new_attribute (cls ,'__replace__',_replace )
    field_list =[f for f in fields .values ()if f ._field_type is _FIELD ]
    if repr :
        flds =[f for f in field_list if f .repr ]
        func_builder .add_fn ('__repr__',
        ('self',),
        ['  return f"{self.__class__.__qualname__}('+
        "".join ([f"{f .name }={{self.{f .name }!r}}"
        for f in flds ])+')"'],
        locals ={'__dataclasses_recursive_repr':recursive_repr },
        decorator ="@__dataclasses_recursive_repr()")
    if eq :
        cmp_fields =(field for field in field_list if field .compare )
        terms =[f'self.{field .name }==other.{field .name }'for field in cmp_fields ]
        field_comparisons =' and '.join (terms )or 'True'
        func_builder .add_fn ('__eq__',
        ('self','other'),
        ['  if self is other:',
        "",
        "",
        f'   return {field_comparisons }',
        ""])
    if order :
        flds =[f for f in field_list if f .compare ]
        self_tuple =_tuple_str ('self',flds )
        other_tuple =_tuple_str ('other',flds )
        for name ,op in [('__lt__','<'),
        ('__le__','<='),
        ('__gt__','>'),
        ('__ge__','>='),
        ]:
            func_builder .add_fn (name ,
            ('self','other'),
            ['  if other.__class__ is self.__class__:',
            f'   return {self_tuple }{op }{other_tuple }',
            ""],
            overwrite_error ='Consider using functools.total_ordering')
    if frozen :
        _frozen_set_del_attr (cls ,field_list ,func_builder )
    hash_action =_hash_action [bool (unsafe_hash ),
    bool (eq ),
    bool (frozen ),
    has_explicit_hash ]
    if hash_action :
        cls .__hash__ =hash_action (cls ,field_list ,func_builder )
    func_builder .add_fns_to_class (cls )
    if not getattr (cls ,'__doc__'):
        try :
            text_sig =str (inspect .signature (cls )).replace (' -> None','')
        except (TypeError ,ValueError ):
            text_sig =''
        cls .__doc__ =(cls .__name__ +text_sig )
    if match_args :
        _set_new_attribute (cls ,'__match_args__',
        tuple (f .name for f in std_init_fields ))
    if weakref_slot and not slots :
        raise TypeError ('weakref_slot is True but slots is False')
    if slots :
        cls =_add_slots (cls ,frozen ,weakref_slot )
    abc .update_abstractmethods (cls )
    return cls
def _dataclass_getstate (self ):
    return [getattr (self ,f .name )for f in fields (self )]
def _dataclass_setstate (self ,state ):
    for field ,value in zip (fields (self ),state ):
        object .__setattr__ (self ,field .name ,value )
def _get_slots (cls ):
    match cls .__dict__ .get ('__slots__'):
        case None :
            slots =[]
            if getattr (cls ,'__weakrefoffset__',-1 )!=0 :
                slots .append ('__weakref__')
            if getattr (cls ,'__dictoffset__',-1 )!=0 :
                slots .append ('__dict__')
            yield from slots
        case str (slot ):
            yield slot
        case iterable if not hasattr (iterable ,'__next__'):
            yield from iterable
        case _ :
            raise TypeError (f"Slots of '{cls .__name__ }' cannot be determined")
def _update_func_cell_for__class__ (f ,oldcls ,newcls ):
    if f is None :
        return False
    try :
        idx =f .__code__ .co_freevars .index ("__class__")
    except ValueError :
        return False
    closure =f .__closure__ [idx ]
    try :
        contents =closure .cell_contents
    except ValueError :
        return False
    if contents is oldcls :
        closure .cell_contents =newcls
        return True
    return False
def _add_slots (cls ,is_frozen ,weakref_slot ):
    if '__slots__'in cls .__dict__ :
        raise TypeError (f'{cls .__name__ } already specifies __slots__')
    cls_dict =dict (cls .__dict__ )
    field_names =tuple (f .name for f in fields (cls ))
    inherited_slots =set (
    itertools .chain .from_iterable (map (_get_slots ,cls .__mro__ [1 :-1 ]))
    )
    cls_dict ["__slots__"]=tuple (
    itertools .filterfalse (
    inherited_slots .__contains__ ,
    itertools .chain (
    field_names ,('__weakref__',)if weakref_slot else ()
    )
    ),
    )
    for field_name in field_names :
        cls_dict .pop (field_name ,None )
    cls_dict .pop ('__dict__',None )
    cls_dict .pop ('__weakref__',None )
    qualname =getattr (cls ,'__qualname__',None )
    newcls =type (cls )(cls .__name__ ,cls .__bases__ ,cls_dict )
    if qualname is not None :
        newcls .__qualname__ =qualname
    if is_frozen :
        if '__getstate__'not in cls_dict :
            newcls .__getstate__ =_dataclass_getstate
        if '__setstate__'not in cls_dict :
            newcls .__setstate__ =_dataclass_setstate
    for member in newcls .__dict__ .values ():
        member =inspect .unwrap (member )
        if isinstance (member ,types .FunctionType ):
            if _update_func_cell_for__class__ (member ,cls ,newcls ):
                break
        elif isinstance (member ,property ):
            if (_update_func_cell_for__class__ (member .fget ,cls ,newcls )
            or _update_func_cell_for__class__ (member .fset ,cls ,newcls )
            or _update_func_cell_for__class__ (member .fdel ,cls ,newcls )):
                break
    return newcls
def dataclass (cls =None ,/,*,init =True ,repr =True ,eq =True ,order =False ,
unsafe_hash =False ,frozen =False ,match_args =True ,
kw_only =False ,slots =False ,weakref_slot =False ):
    def wrap (cls ):
        return _process_class (cls ,init ,repr ,eq ,order ,unsafe_hash ,
        frozen ,match_args ,kw_only ,slots ,
        weakref_slot )
    if cls is None :
        return wrap
    return wrap (cls )
def fields (class_or_instance ):
    try :
        fields =getattr (class_or_instance ,_FIELDS )
    except AttributeError :
        raise TypeError ('must be called with a dataclass type or instance')from None
    return tuple (f for f in fields .values ()if f ._field_type is _FIELD )
def _is_dataclass_instance (obj ):
    return hasattr (type (obj ),_FIELDS )
def is_dataclass (obj ):
    cls =obj if isinstance (obj ,type )else type (obj )
    return hasattr (cls ,_FIELDS )
def asdict (obj ,*,dict_factory =dict ):
    if not _is_dataclass_instance (obj ):
        raise TypeError ("asdict() should be called on dataclass instances")
    return _asdict_inner (obj ,dict_factory )
def _asdict_inner (obj ,dict_factory ):
    obj_type =type (obj )
    if obj_type in _ATOMIC_TYPES :
        return obj
    elif hasattr (obj_type ,_FIELDS ):
        if dict_factory is dict :
            return {
            f .name :_asdict_inner (getattr (obj ,f .name ),dict )
            for f in fields (obj )
            }
        else :
            return dict_factory ([
            (f .name ,_asdict_inner (getattr (obj ,f .name ),dict_factory ))
            for f in fields (obj )
            ])
    elif obj_type is list :
        return [_asdict_inner (v ,dict_factory )for v in obj ]
    elif obj_type is dict :
        return {
        _asdict_inner (k ,dict_factory ):_asdict_inner (v ,dict_factory )
        for k ,v in obj .items ()
        }
    elif obj_type is tuple :
        return tuple ([_asdict_inner (v ,dict_factory )for v in obj ])
    elif issubclass (obj_type ,tuple ):
        if hasattr (obj ,'_fields'):
            return obj_type (*[_asdict_inner (v ,dict_factory )for v in obj ])
        else :
            return obj_type (_asdict_inner (v ,dict_factory )for v in obj )
    elif issubclass (obj_type ,dict ):
        if hasattr (obj_type ,'default_factory'):
            result =obj_type (obj .default_factory )
            for k ,v in obj .items ():
                result [_asdict_inner (k ,dict_factory )]=_asdict_inner (v ,dict_factory )
            return result
        return obj_type ((_asdict_inner (k ,dict_factory ),
        _asdict_inner (v ,dict_factory ))
        for k ,v in obj .items ())
    elif issubclass (obj_type ,list ):
        return obj_type (_asdict_inner (v ,dict_factory )for v in obj )
    else :
        return copy .deepcopy (obj )
def astuple (obj ,*,tuple_factory =tuple ):
    if not _is_dataclass_instance (obj ):
        raise TypeError ("astuple() should be called on dataclass instances")
    return _astuple_inner (obj ,tuple_factory )
def _astuple_inner (obj ,tuple_factory ):
    if type (obj )in _ATOMIC_TYPES :
        return obj
    elif _is_dataclass_instance (obj ):
        return tuple_factory ([
        _astuple_inner (getattr (obj ,f .name ),tuple_factory )
        for f in fields (obj )
        ])
    elif isinstance (obj ,tuple )and hasattr (obj ,'_fields'):
        return type (obj )(*[_astuple_inner (v ,tuple_factory )for v in obj ])
    elif isinstance (obj ,(list ,tuple )):
        return type (obj )(_astuple_inner (v ,tuple_factory )for v in obj )
    elif isinstance (obj ,dict ):
        obj_type =type (obj )
        if hasattr (obj_type ,'default_factory'):
            result =obj_type (getattr (obj ,'default_factory'))
            for k ,v in obj .items ():
                result [_astuple_inner (k ,tuple_factory )]=_astuple_inner (v ,tuple_factory )
            return result
        return obj_type ((_astuple_inner (k ,tuple_factory ),_astuple_inner (v ,tuple_factory ))
        for k ,v in obj .items ())
    else :
        return copy .deepcopy (obj )
def make_dataclass (cls_name ,fields ,*,bases =(),namespace =None ,init =True ,
repr =True ,eq =True ,order =False ,unsafe_hash =False ,
frozen =False ,match_args =True ,kw_only =False ,slots =False ,
weakref_slot =False ,module =None ):
    if namespace is None :
        namespace ={}
    seen =set ()
    annotations ={}
    defaults ={}
    for item in fields :
        if isinstance (item ,str ):
            name =item
            tp ='typing.Any'
        elif len (item )==2 :
            name ,tp ,=item
        elif len (item )==3 :
            name ,tp ,spec =item
            defaults [name ]=spec
        else :
            raise TypeError (f'Invalid field: {item !r }')
        if not isinstance (name ,str )or not name .isidentifier ():
            raise TypeError (f'Field names must be valid identifiers: {name !r }')
        if keyword .iskeyword (name ):
            raise TypeError (f'Field names must not be keywords: {name !r }')
        if name in seen :
            raise TypeError (f'Field name duplicated: {name !r }')
        seen .add (name )
        annotations [name ]=tp
    def exec_body_callback (ns ):
        ns .update (namespace )
        ns .update (defaults )
        ns ['__annotations__']=annotations
    cls =types .new_class (cls_name ,bases ,{},exec_body_callback )
    if module is None :
        try :
            module =sys ._getframemodulename (1 )or '__main__'
        except AttributeError :
            try :
                module =sys ._getframe (1 ).f_globals .get ('__name__','__main__')
            except (AttributeError ,ValueError ):
                pass
    if module is not None :
        cls .__module__ =module
    return dataclass (cls ,init =init ,repr =repr ,eq =eq ,order =order ,
    unsafe_hash =unsafe_hash ,frozen =frozen ,
    match_args =match_args ,kw_only =kw_only ,slots =slots ,
    weakref_slot =weakref_slot )
def replace (obj ,/,**changes ):
    if not _is_dataclass_instance (obj ):
        raise TypeError ("replace() should be called on dataclass instances")
    return _replace (obj ,**changes )
def _replace (self ,/,**changes ):
    for f in getattr (self ,_FIELDS ).values ():
        if f ._field_type is _FIELD_CLASSVAR :
            continue
        if not f .init :
            if f .name in changes :
                raise TypeError (f'field {f .name } is declared with '
                f'init=False, it cannot be specified with '
                f'replace()')
            continue
        if f .name not in changes :
            if f ._field_type is _FIELD_INITVAR and f .default is MISSING :
                raise TypeError (f"InitVar {f .name !r } "
                f'must be specified with replace()')
            changes [f .name ]=getattr (self ,f .name )
    return self .__class__ (**changes )
import re
try :
    from _json import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError :
    c_encode_basestring_ascii =None
try :
    from _json import encode_basestring as c_encode_basestring
except ImportError :
    c_encode_basestring =None
try :
    from _json import make_encoder as c_make_encoder
except ImportError :
    c_make_encoder =None
ESCAPE =re .compile (r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII =re .compile (r'([\\"]|[^\ -~])')
HAS_UTF8 =re .compile (b'[\x80-\xff]')
ESCAPE_DCT ={
"":'\\\\',
"":'\\"',
"":'\\b',
"":'\\f',
"":'\\n',
"":'\\r',
"":'\\t',
}
for i in range (0x20 ):
    ESCAPE_DCT .setdefault (chr (i ),'\\u{0:04x}'.format (i ))
del i
INFINITY =float ('inf')
def py_encode_basestring (s ):
    def replace (match ):
        return ESCAPE_DCT [match .group (0 )]
    return '"'+ESCAPE .sub (replace ,s )+'"'
encode_basestring =(c_encode_basestring or py_encode_basestring )
def py_encode_basestring_ascii (s ):
    def replace (match ):
        s =match .group (0 )
        try :
            return ESCAPE_DCT [s ]
        except KeyError :
            n =ord (s )
            if n <0x10000 :
                return '\\u{0:04x}'.format (n )
            else :
                n -=0x10000
                s1 =0xd800 |((n >>10 )&0x3ff )
                s2 =0xdc00 |(n &0x3ff )
                return '\\u{0:04x}\\u{1:04x}'.format (s1 ,s2 )
    return '"'+ESCAPE_ASCII .sub (replace ,s )+'"'
encode_basestring_ascii =(
c_encode_basestring_ascii or py_encode_basestring_ascii )
class JSONEncoder (object ):
    item_separator =', '
    key_separator =': '
    def __init__ (self ,*,skipkeys =False ,ensure_ascii =True ,
    check_circular =True ,allow_nan =True ,sort_keys =False ,
    indent =None ,separators =None ,default =None ):
        self .skipkeys =skipkeys
        self .ensure_ascii =ensure_ascii
        self .check_circular =check_circular
        self .allow_nan =allow_nan
        self .sort_keys =sort_keys
        self .indent =indent
        if separators is not None :
            self .item_separator ,self .key_separator =separators
        elif indent is not None :
            self .item_separator =','
        if default is not None :
            self .default =default
    def default (self ,o ):
        raise TypeError (f'Object of type {o .__class__ .__name__ } '
        f'is not JSON serializable')
    def encode (self ,o ):
        if isinstance (o ,str ):
            if self .ensure_ascii :
                return encode_basestring_ascii (o )
            else :
                return encode_basestring (o )
        chunks =self .iterencode (o ,_one_shot =True )
        if not isinstance (chunks ,(list ,tuple )):
            chunks =list (chunks )
        return ''.join (chunks )
    def iterencode (self ,o ,_one_shot =False ):
        if self .check_circular :
            markers ={}
        else :
            markers =None
        if self .ensure_ascii :
            _encoder =encode_basestring_ascii
        else :
            _encoder =encode_basestring
        def floatstr (o ,allow_nan =self .allow_nan ,
        _repr =float .__repr__ ,_inf =INFINITY ,_neginf =-INFINITY ):
            if o !=o :
                text ='NaN'
            elif o ==_inf :
                text ='Infinity'
            elif o ==_neginf :
                text ='-Infinity'
            else :
                return _repr (o )
            if not allow_nan :
                raise ValueError (
                ""+
                repr (o ))
            return text
        if self .indent is None or isinstance (self .indent ,str ):
            indent =self .indent
        else :
            indent =' '*self .indent
        if _one_shot and c_make_encoder is not None :
            _iterencode =c_make_encoder (
            markers ,self .default ,_encoder ,indent ,
            self .key_separator ,self .item_separator ,self .sort_keys ,
            self .skipkeys ,self .allow_nan )
        else :
            _iterencode =_make_iterencode (
            markers ,self .default ,_encoder ,indent ,floatstr ,
            self .key_separator ,self .item_separator ,self .sort_keys ,
            self .skipkeys ,_one_shot )
        return _iterencode (o ,0 )
def _make_iterencode (markers ,_default ,_encoder ,_indent ,_floatstr ,
_key_separator ,_item_separator ,_sort_keys ,_skipkeys ,_one_shot ,
ValueError =ValueError ,
dict =dict ,
float =float ,
id =id ,
int =int ,
isinstance =isinstance ,
list =list ,
str =str ,
tuple =tuple ,
_intstr =int .__repr__ ,
):
    def _iterencode_list (lst ,_current_indent_level ):
        if not lst :
            yield '[]'
            return
        if markers is not None :
            markerid =id (lst )
            if markerid in markers :
                raise ValueError ("Circular reference detected")
            markers [markerid ]=lst
        buf ='['
        if _indent is not None :
            _current_indent_level +=1
            newline_indent ='\n'+_indent *_current_indent_level
            separator =_item_separator +newline_indent
            buf +=newline_indent
        else :
            newline_indent =None
            separator =_item_separator
        first =True
        for value in lst :
            if first :
                first =False
            else :
                buf =separator
            if isinstance (value ,str ):
                yield buf +_encoder (value )
            elif value is None :
                yield buf +'null'
            elif value is True :
                yield buf +'true'
            elif value is False :
                yield buf +'false'
            elif isinstance (value ,int ):
                yield buf +_intstr (value )
            elif isinstance (value ,float ):
                yield buf +_floatstr (value )
            else :
                yield buf
                if isinstance (value ,(list ,tuple )):
                    chunks =_iterencode_list (value ,_current_indent_level )
                elif isinstance (value ,dict ):
                    chunks =_iterencode_dict (value ,_current_indent_level )
                else :
                    chunks =_iterencode (value ,_current_indent_level )
                yield from chunks
        if newline_indent is not None :
            _current_indent_level -=1
            yield '\n'+_indent *_current_indent_level
        yield ']'
        if markers is not None :
            del markers [markerid ]
    def _iterencode_dict (dct ,_current_indent_level ):
        if not dct :
            yield '{}'
            return
        if markers is not None :
            markerid =id (dct )
            if markerid in markers :
                raise ValueError ("Circular reference detected")
            markers [markerid ]=dct
        yield '{'
        if _indent is not None :
            _current_indent_level +=1
            newline_indent ='\n'+_indent *_current_indent_level
            item_separator =_item_separator +newline_indent
        else :
            newline_indent =None
            item_separator =_item_separator
        first =True
        if _sort_keys :
            items =sorted (dct .items ())
        else :
            items =dct .items ()
        for key ,value in items :
            if isinstance (key ,str ):
                pass
            elif isinstance (key ,float ):
                key =_floatstr (key )
            elif key is True :
                key ='true'
            elif key is False :
                key ='false'
            elif key is None :
                key ='null'
            elif isinstance (key ,int ):
                key =_intstr (key )
            elif _skipkeys :
                continue
            else :
                raise TypeError (f'keys must be str, int, float, bool or None, '
                f'not {key .__class__ .__name__ }')
            if first :
                first =False
                if newline_indent is not None :
                    yield newline_indent
            else :
                yield item_separator
            yield _encoder (key )
            yield _key_separator
            if isinstance (value ,str ):
                yield _encoder (value )
            elif value is None :
                yield 'null'
            elif value is True :
                yield 'true'
            elif value is False :
                yield 'false'
            elif isinstance (value ,int ):
                yield _intstr (value )
            elif isinstance (value ,float ):
                yield _floatstr (value )
            else :
                if isinstance (value ,(list ,tuple )):
                    chunks =_iterencode_list (value ,_current_indent_level )
                elif isinstance (value ,dict ):
                    chunks =_iterencode_dict (value ,_current_indent_level )
                else :
                    chunks =_iterencode (value ,_current_indent_level )
                yield from chunks
        if not first and newline_indent is not None :
            _current_indent_level -=1
            yield '\n'+_indent *_current_indent_level
        yield '}'
        if markers is not None :
            del markers [markerid ]
    def _iterencode (o ,_current_indent_level ):
        if isinstance (o ,str ):
            yield _encoder (o )
        elif o is None :
            yield 'null'
        elif o is True :
            yield 'true'
        elif o is False :
            yield 'false'
        elif isinstance (o ,int ):
            yield _intstr (o )
        elif isinstance (o ,float ):
            yield _floatstr (o )
        elif isinstance (o ,(list ,tuple )):
            yield from _iterencode_list (o ,_current_indent_level )
        elif isinstance (o ,dict ):
            yield from _iterencode_dict (o ,_current_indent_level )
        else :
            if markers is not None :
                markerid =id (o )
                if markerid in markers :
                    raise ValueError ("Circular reference detected")
                markers [markerid ]=o
            o =_default (o )
            yield from _iterencode (o ,_current_indent_level )
            if markers is not None :
                del markers [markerid ]
    return _iterencode
from collections .abc import Iterable ,MutableMapping
from collections import ChainMap as _ChainMap
import contextlib
import functools
import io
import itertools
import os
import re
import sys
import types
__all__ =("NoSectionError","DuplicateOptionError","DuplicateSectionError",
"","InterpolationError","InterpolationDepthError",
"","InterpolationSyntaxError",
"","MissingSectionHeaderError",
"",
"","RawConfigParser",
"","BasicInterpolation","ExtendedInterpolation",
"","ConverterMapping",
"","MAX_INTERPOLATION_DEPTH","UNNAMED_SECTION")
_default_dict =dict
DEFAULTSECT ="DEFAULT"
MAX_INTERPOLATION_DEPTH =10
class Error (Exception ):
    def __init__ (self ,msg =''):
        self .message =msg
        Exception .__init__ (self ,msg )
    def __repr__ (self ):
        return self .message
    __str__ =__repr__
class NoSectionError (Error ):
    def __init__ (self ,section ):
        Error .__init__ (self ,'No section: %r'%(section ,))
        self .section =section
        self .args =(section ,)
class DuplicateSectionError (Error ):
    def __init__ (self ,section ,source =None ,lineno =None ):
        msg =[repr (section )," already exists"]
        if source is not None :
            message =["While reading from ",repr (source )]
            if lineno is not None :
                message .append (" [line {0:2d}]".format (lineno ))
            message .append (": section ")
            message .extend (msg )
            msg =message
        else :
            msg .insert (0 ,"Section ")
        Error .__init__ (self ,"".join (msg ))
        self .section =section
        self .source =source
        self .lineno =lineno
        self .args =(section ,source ,lineno )
class DuplicateOptionError (Error ):
    def __init__ (self ,section ,option ,source =None ,lineno =None ):
        msg =[repr (option )," in section ",repr (section ),
        ""]
        if source is not None :
            message =["While reading from ",repr (source )]
            if lineno is not None :
                message .append (" [line {0:2d}]".format (lineno ))
            message .append (": option ")
            message .extend (msg )
            msg =message
        else :
            msg .insert (0 ,"Option ")
        Error .__init__ (self ,"".join (msg ))
        self .section =section
        self .option =option
        self .source =source
        self .lineno =lineno
        self .args =(section ,option ,source ,lineno )
class NoOptionError (Error ):
    def __init__ (self ,option ,section ):
        Error .__init__ (self ,"No option %r in section: %r"%
        (option ,section ))
        self .option =option
        self .section =section
        self .args =(option ,section )
class InterpolationError (Error ):
    def __init__ (self ,option ,section ,msg ):
        Error .__init__ (self ,msg )
        self .option =option
        self .section =section
        self .args =(option ,section ,msg )
class InterpolationMissingOptionError (InterpolationError ):
    def __init__ (self ,option ,section ,rawval ,reference ):
        msg =("Bad value substitution: option {!r} in section {!r} contains "
        "".format (option ,section ,reference ,rawval ))
        InterpolationError .__init__ (self ,option ,section ,msg )
        self .reference =reference
        self .args =(option ,section ,rawval ,reference )
class InterpolationSyntaxError (InterpolationError ):
class InterpolationDepthError (InterpolationError ):
    def __init__ (self ,option ,section ,rawval ):
        msg =("Recursion limit exceeded in value substitution: option {!r} "
        "".format (option ,section ,MAX_INTERPOLATION_DEPTH ,
        rawval ))
        InterpolationError .__init__ (self ,option ,section ,msg )
        self .args =(option ,section ,rawval )
class ParsingError (Error ):
    def __init__ (self ,source ,*args ):
        super ().__init__ (f'Source contains parsing errors: {source !r }')
        self .source =source
        self .errors =[]
        self .args =(source ,)
        if args :
            self .append (*args )
    def append (self ,lineno ,line ):
        self .errors .append ((lineno ,line ))
        self .message +=f'\n\t[line {lineno :2d}]: {line !r }'
    def combine (self ,others ):
        messages =[self .message ]
        for other in others :
            for lineno ,line in other .errors :
                self .errors .append ((lineno ,line ))
                messages .append (f'\n\t[line {lineno :2d}]: {line !r }')
        self .message ="".join (messages )
        return self
    @staticmethod
    def _raise_all (exceptions :Iterable ['ParsingError']):
        exceptions =iter (exceptions )
        with contextlib .suppress (StopIteration ):
            raise next (exceptions ).combine (exceptions )
class MissingSectionHeaderError (ParsingError ):
    def __init__ (self ,filename ,lineno ,line ):
        Error .__init__ (
        self ,
        ""%
        (filename ,lineno ,line ))
        self .source =filename
        self .lineno =lineno
        self .line =line
        self .args =(filename ,lineno ,line )
class MultilineContinuationError (ParsingError ):
    def __init__ (self ,filename ,lineno ,line ):
        Error .__init__ (
        self ,
        %(filename ,lineno ,line ))
        self .source =filename
        self .lineno =lineno
        self .line =line
        self .args =(filename ,lineno ,line )
class _UnnamedSection :
    def __repr__ (self ):
        return "<UNNAMED_SECTION>"
UNNAMED_SECTION =_UnnamedSection ()
_UNSET =object ()
class Interpolation :
    def before_get (self ,parser ,section ,option ,value ,defaults ):
        return value
    def before_set (self ,parser ,section ,option ,value ):
        return value
    def before_read (self ,parser ,section ,option ,value ):
        return value
    def before_write (self ,parser ,section ,option ,value ):
        return value
class BasicInterpolation (Interpolation ):
    _KEYCRE =re .compile (r"%\(([^)]+)\)s")
    def before_get (self ,parser ,section ,option ,value ,defaults ):
        L =[]
        self ._interpolate_some (parser ,option ,L ,value ,section ,defaults ,1 )
        return ''.join (L )
    def before_set (self ,parser ,section ,option ,value ):
        tmp_value =value .replace ('%%','')
        tmp_value =self ._KEYCRE .sub ('',tmp_value )
        if '%'in tmp_value :
            raise ValueError ("invalid interpolation syntax in %r at "
            ""%(value ,tmp_value .find ('%')))
        return value
    def _interpolate_some (self ,parser ,option ,accum ,rest ,section ,map ,
    depth ):
        rawval =parser .get (section ,option ,raw =True ,fallback =rest )
        if depth >MAX_INTERPOLATION_DEPTH :
            raise InterpolationDepthError (option ,section ,rawval )
        while rest :
            p =rest .find ("%")
            if p <0 :
                accum .append (rest )
                return
            if p >0 :
                accum .append (rest [:p ])
                rest =rest [p :]
            c =rest [1 :2 ]
            if c =="%":
                accum .append ("%")
                rest =rest [2 :]
            elif c =="(":
                m =self ._KEYCRE .match (rest )
                if m is None :
                    raise InterpolationSyntaxError (option ,section ,
                    ""%rest )
                var =parser .optionxform (m .group (1 ))
                rest =rest [m .end ():]
                try :
                    v =map [var ]
                except KeyError :
                    raise InterpolationMissingOptionError (
                    option ,section ,rawval ,var )from None
                if "%"in v :
                    self ._interpolate_some (parser ,option ,accum ,v ,
                    section ,map ,depth +1 )
                else :
                    accum .append (v )
            else :
                raise InterpolationSyntaxError (
                option ,section ,
                ""%(rest ,))
class ExtendedInterpolation (Interpolation ):
    _KEYCRE =re .compile (r"\$\{([^}]+)\}")
    def before_get (self ,parser ,section ,option ,value ,defaults ):
        L =[]
        self ._interpolate_some (parser ,option ,L ,value ,section ,defaults ,1 )
        return ''.join (L )
    def before_set (self ,parser ,section ,option ,value ):
        tmp_value =value .replace ('$$','')
        tmp_value =self ._KEYCRE .sub ('',tmp_value )
        if '$'in tmp_value :
            raise ValueError ("invalid interpolation syntax in %r at "
            ""%(value ,tmp_value .find ('$')))
        return value
    def _interpolate_some (self ,parser ,option ,accum ,rest ,section ,map ,
    depth ):
        rawval =parser .get (section ,option ,raw =True ,fallback =rest )
        if depth >MAX_INTERPOLATION_DEPTH :
            raise InterpolationDepthError (option ,section ,rawval )
        while rest :
            p =rest .find ("$")
            if p <0 :
                accum .append (rest )
                return
            if p >0 :
                accum .append (rest [:p ])
                rest =rest [p :]
            c =rest [1 :2 ]
            if c =="$":
                accum .append ("$")
                rest =rest [2 :]
            elif c =="{":
                m =self ._KEYCRE .match (rest )
                if m is None :
                    raise InterpolationSyntaxError (option ,section ,
                    ""%rest )
                path =m .group (1 ).split (':')
                rest =rest [m .end ():]
                sect =section
                opt =option
                try :
                    if len (path )==1 :
                        opt =parser .optionxform (path [0 ])
                        v =map [opt ]
                    elif len (path )==2 :
                        sect =path [0 ]
                        opt =parser .optionxform (path [1 ])
                        v =parser .get (sect ,opt ,raw =True )
                    else :
                        raise InterpolationSyntaxError (
                        option ,section ,
                        ""%(rest ,))
                except (KeyError ,NoSectionError ,NoOptionError ):
                    raise InterpolationMissingOptionError (
                    option ,section ,rawval ,":".join (path ))from None
                if v is None :
                    continue
                if "$"in v :
                    self ._interpolate_some (parser ,opt ,accum ,v ,sect ,
                    dict (parser .items (sect ,raw =True )),
                    depth +1 )
                else :
                    accum .append (v )
            else :
                raise InterpolationSyntaxError (
                option ,section ,
                ""%(rest ,))
class _ReadState :
    elements_added :set [str ]
    cursect :dict [str ,str ]|None =None
    sectname :str |None =None
    optname :str |None =None
    lineno :int =0
    indent_level :int =0
    errors :list [ParsingError ]
    def __init__ (self ):
        self .elements_added =set ()
        self .errors =list ()
class _Line (str ):
    def __new__ (cls ,val ,*args ,**kwargs ):
        return super ().__new__ (cls ,val )
    def __init__ (self ,val ,prefixes ):
        self .prefixes =prefixes
    @functools .cached_property
    def clean (self ):
        return self ._strip_full ()and self ._strip_inline ()
    @property
    def has_comments (self ):
        return self .strip ()!=self .clean
    def _strip_inline (self ):
        matcher =re .compile (
        "".join (fr'(^|\s)({re .escape (prefix )})'for prefix in self .prefixes .inline )
        or '(?!)'
        )
        match =matcher .search (self )
        return self [:match .start ()if match else None ].strip ()
    def _strip_full (self ):
        return ''if any (map (self .strip ().startswith ,self .prefixes .full ))else True
class RawConfigParser (MutableMapping ):
    _SECT_TMPL =r"""
        \[                                 # [
        (?P<header>.+)                     # very permissive!
        \]                                 # ]
        """
    _OPT_TMPL =r"""
        (?P<option>                        # very permissive!
            (?:(?!{delim})\S)*             # non-delimiter non-whitespace
            (?:(?:(?!{delim})\s)+          # optionally more
             (?:(?!{delim})\S)+)*)         #   space-separated words
        \s*(?P<vi>{delim})\s*              # any number of space/tab,
                                           # followed by any of the
                                           # allowed delimiters,
                                           # followed by any space/tab
        (?P<value>.*)$                     # everything up to eol
        """
    _OPT_NV_TMPL =r"""
        (?P<option>                        # very permissive!
            (?:(?!{delim})\S)*             # non-delimiter non-whitespace
            (?:(?:(?!{delim})\s)+          # optionally more
             (?:(?!{delim})\S)+)*)         #   space-separated words
        \s*(?:                             # any number of space/tab,
        (?P<vi>{delim})\s*                 # optionally followed by
                                           # any of the allowed
                                           # delimiters, followed by any
                                           # space/tab
        (?P<value>.*))?$                   # everything up to eol
        """
    _DEFAULT_INTERPOLATION =Interpolation ()
    SECTCRE =re .compile (_SECT_TMPL ,re .VERBOSE )
    OPTCRE =re .compile (_OPT_TMPL .format (delim ="=|:"),re .VERBOSE )
    OPTCRE_NV =re .compile (_OPT_NV_TMPL .format (delim ="=|:"),re .VERBOSE )
    NONSPACECRE =re .compile (r"\S")
    BOOLEAN_STATES ={'1':True ,'yes':True ,'true':True ,'on':True ,
    "":False ,'no':False ,'false':False ,'off':False }
    def __init__ (self ,defaults =None ,dict_type =_default_dict ,
    allow_no_value =False ,*,delimiters =('=',':'),
    comment_prefixes =('#',';'),inline_comment_prefixes =None ,
    strict =True ,empty_lines_in_values =True ,
    default_section =DEFAULTSECT ,
    interpolation =_UNSET ,converters =_UNSET ,
    allow_unnamed_section =False ,):
        self ._dict =dict_type
        self ._sections =self ._dict ()
        self ._defaults =self ._dict ()
        self ._converters =ConverterMapping (self )
        self ._proxies =self ._dict ()
        self ._proxies [default_section ]=SectionProxy (self ,default_section )
        self ._delimiters =tuple (delimiters )
        if delimiters ==('=',':'):
            self ._optcre =self .OPTCRE_NV if allow_no_value else self .OPTCRE
        else :
            d ="|".join (re .escape (d )for d in delimiters )
            if allow_no_value :
                self ._optcre =re .compile (self ._OPT_NV_TMPL .format (delim =d ),
                re .VERBOSE )
            else :
                self ._optcre =re .compile (self ._OPT_TMPL .format (delim =d ),
                re .VERBOSE )
        self ._prefixes =types .SimpleNamespace (
        full =tuple (comment_prefixes or ()),
        inline =tuple (inline_comment_prefixes or ()),
        )
        self ._strict =strict
        self ._allow_no_value =allow_no_value
        self ._empty_lines_in_values =empty_lines_in_values
        self .default_section =default_section
        self ._interpolation =interpolation
        if self ._interpolation is _UNSET :
            self ._interpolation =self ._DEFAULT_INTERPOLATION
        if self ._interpolation is None :
            self ._interpolation =Interpolation ()
        if not isinstance (self ._interpolation ,Interpolation ):
            raise TypeError (
            f"interpolation= must be None or an instance of Interpolation;"
            f" got an object of type {type (self ._interpolation )}"
            )
        if converters is not _UNSET :
            self ._converters .update (converters )
        if defaults :
            self ._read_defaults (defaults )
        self ._allow_unnamed_section =allow_unnamed_section
    def defaults (self ):
        return self ._defaults
    def sections (self ):
        return list (self ._sections .keys ())
    def add_section (self ,section ):
        if section ==self .default_section :
            raise ValueError ('Invalid section name: %r'%section )
        if section in self ._sections :
            raise DuplicateSectionError (section )
        self ._sections [section ]=self ._dict ()
        self ._proxies [section ]=SectionProxy (self ,section )
    def has_section (self ,section ):
        return section in self ._sections
    def options (self ,section ):
        try :
            opts =self ._sections [section ].copy ()
        except KeyError :
            raise NoSectionError (section )from None
        opts .update (self ._defaults )
        return list (opts .keys ())
    def read (self ,filenames ,encoding =None ):
        if isinstance (filenames ,(str ,bytes ,os .PathLike )):
            filenames =[filenames ]
        encoding =io .text_encoding (encoding )
        read_ok =[]
        for filename in filenames :
            try :
                with open (filename ,encoding =encoding )as fp :
                    self ._read (fp ,filename )
            except OSError :
                continue
            if isinstance (filename ,os .PathLike ):
                filename =os .fspath (filename )
            read_ok .append (filename )
        return read_ok
    def read_file (self ,f ,source =None ):
        if source is None :
            try :
                source =f .name
            except AttributeError :
                source ='<???>'
        self ._read (f ,source )
    def read_string (self ,string ,source ='<string>'):
        sfile =io .StringIO (string )
        self .read_file (sfile ,source )
    def read_dict (self ,dictionary ,source ='<dict>'):
        elements_added =set ()
        for section ,keys in dictionary .items ():
            section =str (section )
            try :
                self .add_section (section )
            except (DuplicateSectionError ,ValueError ):
                if self ._strict and section in elements_added :
                    raise
            elements_added .add (section )
            for key ,value in keys .items ():
                key =self .optionxform (str (key ))
                if value is not None :
                    value =str (value )
                if self ._strict and (section ,key )in elements_added :
                    raise DuplicateOptionError (section ,key ,source )
                elements_added .add ((section ,key ))
                self .set (section ,key ,value )
    def get (self ,section ,option ,*,raw =False ,vars =None ,fallback =_UNSET ):
        try :
            d =self ._unify_values (section ,vars )
        except NoSectionError :
            if fallback is _UNSET :
                raise
            else :
                return fallback
        option =self .optionxform (option )
        try :
            value =d [option ]
        except KeyError :
            if fallback is _UNSET :
                raise NoOptionError (option ,section )
            else :
                return fallback
        if raw or value is None :
            return value
        else :
            return self ._interpolation .before_get (self ,section ,option ,value ,
            d )
    def _get (self ,section ,conv ,option ,**kwargs ):
        return conv (self .get (section ,option ,**kwargs ))
    def _get_conv (self ,section ,option ,conv ,*,raw =False ,vars =None ,
    fallback =_UNSET ,**kwargs ):
        try :
            return self ._get (section ,conv ,option ,raw =raw ,vars =vars ,
            **kwargs )
        except (NoSectionError ,NoOptionError ):
            if fallback is _UNSET :
                raise
            return fallback
    def getint (self ,section ,option ,*,raw =False ,vars =None ,
    fallback =_UNSET ,**kwargs ):
        return self ._get_conv (section ,option ,int ,raw =raw ,vars =vars ,
        fallback =fallback ,**kwargs )
    def getfloat (self ,section ,option ,*,raw =False ,vars =None ,
    fallback =_UNSET ,**kwargs ):
        return self ._get_conv (section ,option ,float ,raw =raw ,vars =vars ,
        fallback =fallback ,**kwargs )
    def getboolean (self ,section ,option ,*,raw =False ,vars =None ,
    fallback =_UNSET ,**kwargs ):
        return self ._get_conv (section ,option ,self ._convert_to_boolean ,
        raw =raw ,vars =vars ,fallback =fallback ,**kwargs )
    def items (self ,section =_UNSET ,raw =False ,vars =None ):
        if section is _UNSET :
            return super ().items ()
        d =self ._defaults .copy ()
        try :
            d .update (self ._sections [section ])
        except KeyError :
            if section !=self .default_section :
                raise NoSectionError (section )
        orig_keys =list (d .keys ())
        if vars :
            for key ,value in vars .items ():
                d [self .optionxform (key )]=value
        value_getter =lambda option :self ._interpolation .before_get (self ,
        section ,option ,d [option ],d )
        if raw :
            value_getter =lambda option :d [option ]
        return [(option ,value_getter (option ))for option in orig_keys ]
    def popitem (self ):
        for key in self .sections ():
            value =self [key ]
            del self [key ]
            return key ,value
        raise KeyError
    def optionxform (self ,optionstr ):
        return optionstr .lower ()
    def has_option (self ,section ,option ):
        if not section or section ==self .default_section :
            option =self .optionxform (option )
            return option in self ._defaults
        elif section not in self ._sections :
            return False
        else :
            option =self .optionxform (option )
            return (option in self ._sections [section ]
            or option in self ._defaults )
    def set (self ,section ,option ,value =None ):
        if value :
            value =self ._interpolation .before_set (self ,section ,option ,
            value )
        if not section or section ==self .default_section :
            sectdict =self ._defaults
        else :
            try :
                sectdict =self ._sections [section ]
            except KeyError :
                raise NoSectionError (section )from None
        sectdict [self .optionxform (option )]=value
    def write (self ,fp ,space_around_delimiters =True ):
        if space_around_delimiters :
            d =" {} ".format (self ._delimiters [0 ])
        else :
            d =self ._delimiters [0 ]
        if self ._defaults :
            self ._write_section (fp ,self .default_section ,
            self ._defaults .items (),d )
        if UNNAMED_SECTION in self ._sections :
            self ._write_section (fp ,UNNAMED_SECTION ,self ._sections [UNNAMED_SECTION ].items (),d ,unnamed =True )
        for section in self ._sections :
            if section is UNNAMED_SECTION :
                continue
            self ._write_section (fp ,section ,
            self ._sections [section ].items (),d )
    def _write_section (self ,fp ,section_name ,section_items ,delimiter ,unnamed =False ):
        if not unnamed :
            fp .write ("[{}]\n".format (section_name ))
        for key ,value in section_items :
            value =self ._interpolation .before_write (self ,section_name ,key ,
            value )
            if value is not None or not self ._allow_no_value :
                value =(delimiter +str (value ).replace ('\r\n','\n')
                .replace ('\r','\n').replace ('\n','\n\t'))
            else :
                value =""
            fp .write ("{}{}\n".format (key ,value ))
        fp .write ("\n")
    def remove_option (self ,section ,option ):
        if not section or section ==self .default_section :
            sectdict =self ._defaults
        else :
            try :
                sectdict =self ._sections [section ]
            except KeyError :
                raise NoSectionError (section )from None
        option =self .optionxform (option )
        existed =option in sectdict
        if existed :
            del sectdict [option ]
        return existed
    def remove_section (self ,section ):
        existed =section in self ._sections
        if existed :
            del self ._sections [section ]
            del self ._proxies [section ]
        return existed
    def __getitem__ (self ,key ):
        if key !=self .default_section and not self .has_section (key ):
            raise KeyError (key )
        return self ._proxies [key ]
    def __setitem__ (self ,key ,value ):
        if key in self and self [key ]is value :
            return
        if key ==self .default_section :
            self ._defaults .clear ()
        elif key in self ._sections :
            self ._sections [key ].clear ()
        self .read_dict ({key :value })
    def __delitem__ (self ,key ):
        if key ==self .default_section :
            raise ValueError ("Cannot remove the default section.")
        if not self .has_section (key ):
            raise KeyError (key )
        self .remove_section (key )
    def __contains__ (self ,key ):
        return key ==self .default_section or self .has_section (key )
    def __len__ (self ):
        return len (self ._sections )+1
    def __iter__ (self ):
        return itertools .chain ((self .default_section ,),self ._sections .keys ())
    def _read (self ,fp ,fpname ):
        try :
            ParsingError ._raise_all (self ._read_inner (fp ,fpname ))
        finally :
            self ._join_multiline_values ()
    def _read_inner (self ,fp ,fpname ):
        st =_ReadState ()
        Line =functools .partial (_Line ,prefixes =self ._prefixes )
        for st .lineno ,line in enumerate (map (Line ,fp ),start =1 ):
            if not line .clean :
                if self ._empty_lines_in_values :
                    if (not line .has_comments and
                    st .cursect is not None and
                    st .optname and
                    st .cursect [st .optname ]is not None ):
                        st .cursect [st .optname ].append ('')
                else :
                    st .indent_level =sys .maxsize
                continue
            first_nonspace =self .NONSPACECRE .search (line )
            st .cur_indent_level =first_nonspace .start ()if first_nonspace else 0
            if self ._handle_continuation_line (st ,line ,fpname ):
                continue
            self ._handle_rest (st ,line ,fpname )
        return st .errors
    def _handle_continuation_line (self ,st ,line ,fpname ):
        is_continue =(st .cursect is not None and st .optname and
        st .cur_indent_level >st .indent_level )
        if is_continue :
            if st .cursect [st .optname ]is None :
                raise MultilineContinuationError (fpname ,st .lineno ,line )
            st .cursect [st .optname ].append (line .clean )
        return is_continue
    def _handle_rest (self ,st ,line ,fpname ):
        if self ._allow_unnamed_section and st .cursect is None :
            self ._handle_header (st ,UNNAMED_SECTION ,fpname )
        st .indent_level =st .cur_indent_level
        mo =self .SECTCRE .match (line .clean )
        if not mo and st .cursect is None :
            raise MissingSectionHeaderError (fpname ,st .lineno ,line )
        self ._handle_header (st ,mo .group ('header'),fpname )if mo else self ._handle_option (st ,line ,fpname )
    def _handle_header (self ,st ,sectname ,fpname ):
        st .sectname =sectname
        if st .sectname in self ._sections :
            if self ._strict and st .sectname in st .elements_added :
                raise DuplicateSectionError (st .sectname ,fpname ,
                st .lineno )
            st .cursect =self ._sections [st .sectname ]
            st .elements_added .add (st .sectname )
        elif st .sectname ==self .default_section :
            st .cursect =self ._defaults
        else :
            st .cursect =self ._dict ()
            self ._sections [st .sectname ]=st .cursect
            self ._proxies [st .sectname ]=SectionProxy (self ,st .sectname )
            st .elements_added .add (st .sectname )
        st .optname =None
    def _handle_option (self ,st ,line ,fpname ):
        st .indent_level =st .cur_indent_level
        mo =self ._optcre .match (line .clean )
        if not mo :
            st .errors .append (ParsingError (fpname ,st .lineno ,line ))
            return
        st .optname ,vi ,optval =mo .group ('option','vi','value')
        if not st .optname :
            st .errors .append (ParsingError (fpname ,st .lineno ,line ))
        st .optname =self .optionxform (st .optname .rstrip ())
        if (self ._strict and
        (st .sectname ,st .optname )in st .elements_added ):
            raise DuplicateOptionError (st .sectname ,st .optname ,
            fpname ,st .lineno )
        st .elements_added .add ((st .sectname ,st .optname ))
        if optval is not None :
            optval =optval .strip ()
            st .cursect [st .optname ]=[optval ]
        else :
            st .cursect [st .optname ]=None
    def _join_multiline_values (self ):
        defaults =self .default_section ,self ._defaults
        all_sections =itertools .chain ((defaults ,),
        self ._sections .items ())
        for section ,options in all_sections :
            for name ,val in options .items ():
                if isinstance (val ,list ):
                    val ='\n'.join (val ).rstrip ()
                options [name ]=self ._interpolation .before_read (self ,
                section ,
                name ,val )
    def _read_defaults (self ,defaults ):
        for key ,value in defaults .items ():
            self ._defaults [self .optionxform (key )]=value
    def _unify_values (self ,section ,vars ):
        sectiondict ={}
        try :
            sectiondict =self ._sections [section ]
        except KeyError :
            if section !=self .default_section :
                raise NoSectionError (section )from None
        vardict ={}
        if vars :
            for key ,value in vars .items ():
                if value is not None :
                    value =str (value )
                vardict [self .optionxform (key )]=value
        return _ChainMap (vardict ,sectiondict ,self ._defaults )
    def _convert_to_boolean (self ,value ):
        if value .lower ()not in self .BOOLEAN_STATES :
            raise ValueError ('Not a boolean: %s'%value )
        return self .BOOLEAN_STATES [value .lower ()]
    def _validate_value_types (self ,*,section ="",option ="",value =""):
        if not isinstance (section ,str ):
            raise TypeError ("section names must be strings")
        if not isinstance (option ,str ):
            raise TypeError ("option keys must be strings")
        if not self ._allow_no_value or value :
            if not isinstance (value ,str ):
                raise TypeError ("option values must be strings")
    @property
    def converters (self ):
        return self ._converters
class ConfigParser (RawConfigParser ):
    _DEFAULT_INTERPOLATION =BasicInterpolation ()
    def set (self ,section ,option ,value =None ):
        self ._validate_value_types (option =option ,value =value )
        super ().set (section ,option ,value )
    def add_section (self ,section ):
        self ._validate_value_types (section =section )
        super ().add_section (section )
    def _read_defaults (self ,defaults ):
        try :
            hold_interpolation =self ._interpolation
            self ._interpolation =Interpolation ()
            self .read_dict ({self .default_section :defaults })
        finally :
            self ._interpolation =hold_interpolation
class SectionProxy (MutableMapping ):
    def __init__ (self ,parser ,name ):
        self ._parser =parser
        self ._name =name
        for conv in parser .converters :
            key ='get'+conv
            getter =functools .partial (self .get ,_impl =getattr (parser ,key ))
            setattr (self ,key ,getter )
    def __repr__ (self ):
        return '<Section: {}>'.format (self ._name )
    def __getitem__ (self ,key ):
        if not self ._parser .has_option (self ._name ,key ):
            raise KeyError (key )
        return self ._parser .get (self ._name ,key )
    def __setitem__ (self ,key ,value ):
        self ._parser ._validate_value_types (option =key ,value =value )
        return self ._parser .set (self ._name ,key ,value )
    def __delitem__ (self ,key ):
        if not (self ._parser .has_option (self ._name ,key )and
        self ._parser .remove_option (self ._name ,key )):
            raise KeyError (key )
    def __contains__ (self ,key ):
        return self ._parser .has_option (self ._name ,key )
    def __len__ (self ):
        return len (self ._options ())
    def __iter__ (self ):
        return self ._options ().__iter__ ()
    def _options (self ):
        if self ._name !=self ._parser .default_section :
            return self ._parser .options (self ._name )
        else :
            return self ._parser .defaults ()
    @property
    def parser (self ):
        return self ._parser
    @property
    def name (self ):
        return self ._name
    def get (self ,option ,fallback =None ,*,raw =False ,vars =None ,
    _impl =None ,**kwargs ):
        if not _impl :
            _impl =self ._parser .get
        return _impl (self ._name ,option ,raw =raw ,vars =vars ,
        fallback =fallback ,**kwargs )
class ConverterMapping (MutableMapping ):
    GETTERCRE =re .compile (r"^get(?P<name>.+)$")
    def __init__ (self ,parser ):
        self ._parser =parser
        self ._data ={}
        for getter in dir (self ._parser ):
            m =self .GETTERCRE .match (getter )
            if not m or not callable (getattr (self ._parser ,getter )):
                continue
            self ._data [m .group ('name')]=None
    def __getitem__ (self ,key ):
        return self ._data [key ]
    def __setitem__ (self ,key ,value ):
        try :
            k ='get'+key
        except TypeError :
            raise ValueError ('Incompatible key: {} (type: {})'
            "".format (key ,type (key )))
        if k =='get':
            raise ValueError ('Incompatible key: cannot use "" as a name')
        self ._data [key ]=value
        func =functools .partial (self ._parser ._get_conv ,conv =value )
        func .converter =value
        setattr (self ._parser ,k ,func )
        for proxy in self ._parser .values ():
            getter =functools .partial (proxy .get ,_impl =func )
            setattr (proxy ,k ,getter )
    def __delitem__ (self ,key ):
        try :
            k ='get'+(key or None )
        except TypeError :
            raise KeyError (key )
        del self ._data [key ]
        for inst in itertools .chain ((self ._parser ,),self ._parser .values ()):
            try :
                delattr (inst ,k )
            except AttributeError :
                continue
    def __iter__ (self ):
        return iter (self ._data )
    def __len__ (self ):
        return len (self ._data )
__all__ =[
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
"",
]
import math
import numbers
import random
import sys
from fractions import Fraction
from decimal import Decimal
from itertools import count ,groupby ,repeat
from bisect import bisect_left ,bisect_right
from math import hypot ,sqrt ,fabs ,exp ,erf ,tau ,log ,fsum ,sumprod
from math import isfinite ,isinf ,pi ,cos ,sin ,tan ,cosh ,asin ,atan ,acos
from functools import reduce
from operator import itemgetter
from collections import Counter ,namedtuple ,defaultdict
_SQRT2 =sqrt (2.0 )
_random =random
class StatisticsError (ValueError ):
    pass
def _sum (data ):
    count =0
    types =set ()
    types_add =types .add
    partials ={}
    partials_get =partials .get
    for typ ,values in groupby (data ,type ):
        types_add (typ )
        for n ,d in map (_exact_ratio ,values ):
            count +=1
            partials [d ]=partials_get (d ,0 )+n
    if None in partials :
        total =partials [None ]
        assert not _isfinite (total )
    else :
        total =sum (Fraction (n ,d )for d ,n in partials .items ())
    T =reduce (_coerce ,types ,int )
    return (T ,total ,count )
def _ss (data ,c =None ):
    if c is not None :
        T ,ssd ,count =_sum ((d :=x -c )*d for x in data )
        return (T ,ssd ,c ,count )
    count =0
    types =set ()
    types_add =types .add
    sx_partials =defaultdict (int )
    sxx_partials =defaultdict (int )
    for typ ,values in groupby (data ,type ):
        types_add (typ )
        for n ,d in map (_exact_ratio ,values ):
            count +=1
            sx_partials [d ]+=n
            sxx_partials [d ]+=n *n
    if not count :
        ssd =c =Fraction (0 )
    elif None in sx_partials :
        ssd =c =sx_partials [None ]
        assert not _isfinite (ssd )
    else :
        sx =sum (Fraction (n ,d )for d ,n in sx_partials .items ())
        sxx =sum (Fraction (n ,d *d )for d ,n in sxx_partials .items ())
        ssd =(count *sxx -sx *sx )/count
        c =sx /count
    T =reduce (_coerce ,types ,int )
    return (T ,ssd ,c ,count )
def _isfinite (x ):
    try :
        return x .is_finite ()
    except AttributeError :
        return math .isfinite (x )
def _coerce (T ,S ):
    assert T is not bool ,"initial type T is bool"
    if T is S :return T
    if S is int or S is bool :return T
    if T is int :return S
    if issubclass (S ,T ):return S
    if issubclass (T ,S ):return T
    if issubclass (T ,int ):return S
    if issubclass (S ,int ):return T
    if issubclass (T ,Fraction )and issubclass (S ,float ):
        return S
    if issubclass (T ,float )and issubclass (S ,Fraction ):
        return T
    msg ="don't know how to coerce %s and %s"
    raise TypeError (msg %(T .__name__ ,S .__name__ ))
def _exact_ratio (x ):
    try :
        return x .as_integer_ratio ()
    except AttributeError :
        pass
    except (OverflowError ,ValueError ):
        assert not _isfinite (x )
        return (x ,None )
    try :
        return (x .numerator ,x .denominator )
    except AttributeError :
        msg =f"can't convert type '{type (x ).__name__ }' to numerator/denominator"
        raise TypeError (msg )
def _convert (value ,T ):
    if type (value )is T :
        return value
    if issubclass (T ,int )and value .denominator !=1 :
        T =float
    try :
        return T (value )
    except TypeError :
        if issubclass (T ,Decimal ):
            return T (value .numerator )/T (value .denominator )
        else :
            raise
def _fail_neg (values ,errmsg ='negative value'):
    for x in values :
        if x <0 :
            raise StatisticsError (errmsg )
        yield x
def _rank (data ,/,*,key =None ,reverse =False ,ties ='average',start =1 )->list [float ]:
    if ties !='average':
        raise ValueError (f'Unknown tie resolution method: {ties !r }')
    if key is not None :
        data =map (key ,data )
    val_pos =sorted (zip (data ,count ()),reverse =reverse )
    i =start -1
    result =[0 ]*len (val_pos )
    for _ ,g in groupby (val_pos ,key =itemgetter (0 )):
        group =list (g )
        size =len (group )
        rank =i +(size +1 )/2
        for value ,orig_pos in group :
            result [orig_pos ]=rank
        i +=size
    return result
def _integer_sqrt_of_frac_rto (n :int ,m :int )->int :
    a =math .isqrt (n //m )
    return a |(a *a *m !=n )
_sqrt_bit_width :int =2 *sys .float_info .mant_dig +3
def _float_sqrt_of_frac (n :int ,m :int )->float :
    q =(n .bit_length ()-m .bit_length ()-_sqrt_bit_width )//2
    if q >=0 :
        numerator =_integer_sqrt_of_frac_rto (n ,m <<2 *q )<<q
        denominator =1
    else :
        numerator =_integer_sqrt_of_frac_rto (n <<-2 *q ,m )
        denominator =1 <<-q
    return numerator /denominator
def _decimal_sqrt_of_frac (n :int ,m :int )->Decimal :
    if n <=0 :
        if not n :
            return Decimal ('0.0')
        n ,m =-n ,-m
    root =(Decimal (n )/Decimal (m )).sqrt ()
    nr ,dr =root .as_integer_ratio ()
    plus =root .next_plus ()
    np ,dp =plus .as_integer_ratio ()
    if 4 *n *(dr *dp )**2 >m *(dr *np +dp *nr )**2 :
        return plus
    minus =root .next_minus ()
    nm ,dm =minus .as_integer_ratio ()
    if 4 *n *(dr *dm )**2 <m *(dr *nm +dm *nr )**2 :
        return minus
    return root
def mean (data ):
    T ,total ,n =_sum (data )
    if n <1 :
        raise StatisticsError ('mean requires at least one data point')
    return _convert (total /n ,T )
def fmean (data ,weights =None ):
    if weights is None :
        try :
            n =len (data )
        except TypeError :
            n =0
            def count (iterable ):
                nonlocal n
                for n ,x in enumerate (iterable ,start =1 ):
                    yield x
            data =count (data )
        total =fsum (data )
        if not n :
            raise StatisticsError ('fmean requires at least one data point')
        return total /n
    if not isinstance (weights ,(list ,tuple )):
        weights =list (weights )
    try :
        num =sumprod (data ,weights )
    except ValueError :
        raise StatisticsError ('data and weights must be the same length')
    den =fsum (weights )
    if not den :
        raise StatisticsError ('sum of weights must be non-zero')
    return num /den
def geometric_mean (data ):
    n =0
    found_zero =False
    def count_positive (iterable ):
        nonlocal n ,found_zero
        for n ,x in enumerate (iterable ,start =1 ):
            if x >0.0 or math .isnan (x ):
                yield x
            elif x ==0.0 :
                found_zero =True
            else :
                raise StatisticsError ('No negative inputs allowed',x )
    total =fsum (map (log ,count_positive (data )))
    if not n :
        raise StatisticsError ('Must have a non-empty dataset')
    if math .isnan (total ):
        return math .nan
    if found_zero :
        return math .nan if total ==math .inf else 0.0
    return exp (total /n )
def harmonic_mean (data ,weights =None ):
    if iter (data )is data :
        data =list (data )
    errmsg ='harmonic mean does not support negative values'
    n =len (data )
    if n <1 :
        raise StatisticsError ('harmonic_mean requires at least one data point')
    elif n ==1 and weights is None :
        x =data [0 ]
        if isinstance (x ,(numbers .Real ,Decimal )):
            if x <0 :
                raise StatisticsError (errmsg )
            return x
        else :
            raise TypeError ('unsupported type')
    if weights is None :
        weights =repeat (1 ,n )
        sum_weights =n
    else :
        if iter (weights )is weights :
            weights =list (weights )
        if len (weights )!=n :
            raise StatisticsError ('Number of weights does not match data size')
        _ ,sum_weights ,_ =_sum (w for w in _fail_neg (weights ,errmsg ))
    try :
        data =_fail_neg (data ,errmsg )
        T ,total ,count =_sum (w /x if w else 0 for w ,x in zip (weights ,data ))
    except ZeroDivisionError :
        return 0
    if total <=0 :
        raise StatisticsError ('Weighted sum must be positive')
    return _convert (sum_weights /total ,T )
def median (data ):
    data =sorted (data )
    n =len (data )
    if n ==0 :
        raise StatisticsError ("no median for empty data")
    if n %2 ==1 :
        return data [n //2 ]
    else :
        i =n //2
        return (data [i -1 ]+data [i ])/2
def median_low (data ):
    data =sorted (data )
    n =len (data )
    if n ==0 :
        raise StatisticsError ("no median for empty data")
    if n %2 ==1 :
        return data [n //2 ]
    else :
        return data [n //2 -1 ]
def median_high (data ):
    data =sorted (data )
    n =len (data )
    if n ==0 :
        raise StatisticsError ("no median for empty data")
    return data [n //2 ]
def median_grouped (data ,interval =1.0 ):
    data =sorted (data )
    n =len (data )
    if not n :
        raise StatisticsError ("no median for empty data")
    x =data [n //2 ]
    i =bisect_left (data ,x )
    j =bisect_right (data ,x ,lo =i )
    try :
        interval =float (interval )
        x =float (x )
    except ValueError :
        raise TypeError (f'Value cannot be converted to a float')
    L =x -interval /2.0
    cf =i
    f =j -i
    return L +interval *(n /2 -cf )/f
def mode (data ):
    pairs =Counter (iter (data )).most_common (1 )
    try :
        return pairs [0 ][0 ]
    except IndexError :
        raise StatisticsError ('no mode for empty data')from None
def multimode (data ):
    counts =Counter (iter (data ))
    if not counts :
        return []
    maxcount =max (counts .values ())
    return [value for value ,count in counts .items ()if count ==maxcount ]
def kde (data ,h ,kernel ='normal',*,cumulative =False ):
    n =len (data )
    if not n :
        raise StatisticsError ('Empty data sequence')
    if not isinstance (data [0 ],(int ,float )):
        raise TypeError ('Data sequence must contain ints or floats')
    if h <=0.0 :
        raise StatisticsError (f'Bandwidth h must be positive, not {h =!r }')
    match kernel :
        case 'normal'|'gauss':
            sqrt2pi =sqrt (2 *pi )
            sqrt2 =sqrt (2 )
            K =lambda t :exp (-1 /2 *t *t )/sqrt2pi
            W =lambda t :1 /2 *(1.0 +erf (t /sqrt2 ))
            support =None
        case 'logistic':
            K =lambda t :1 /2 /(1.0 +cosh (t ))
            W =lambda t :1.0 -1.0 /(exp (t )+1.0 )
            support =None
        case 'sigmoid':
            c1 =1 /pi
            c2 =2 /pi
            K =lambda t :c1 /cosh (t )
            W =lambda t :c2 *atan (exp (t ))
            support =None
        case 'rectangular'|'uniform':
            K =lambda t :1 /2
            W =lambda t :1 /2 *t +1 /2
            support =1.0
        case 'triangular':
            K =lambda t :1.0 -abs (t )
            W =lambda t :t *t *(1 /2 if t <0.0 else -1 /2 )+t +1 /2
            support =1.0
        case 'parabolic'|'epanechnikov':
            K =lambda t :3 /4 *(1.0 -t *t )
            W =lambda t :-1 /4 *t **3 +3 /4 *t +1 /2
            support =1.0
        case 'quartic'|'biweight':
            K =lambda t :15 /16 *(1.0 -t *t )**2
            W =lambda t :3 /16 *t **5 -5 /8 *t **3 +15 /16 *t +1 /2
            support =1.0
        case 'triweight':
            K =lambda t :35 /32 *(1.0 -t *t )**3
            W =lambda t :35 /32 *(-1 /7 *t **7 +3 /5 *t **5 -t **3 +t )+1 /2
            support =1.0
        case 'cosine':
            c1 =pi /4
            c2 =pi /2
            K =lambda t :c1 *cos (c2 *t )
            W =lambda t :1 /2 *sin (c2 *t )+1 /2
            support =1.0
        case _ :
            raise StatisticsError (f'Unknown kernel name: {kernel !r }')
    if support is None :
        def pdf (x ):
            n =len (data )
            return sum (K ((x -x_i )/h )for x_i in data )/(n *h )
        def cdf (x ):
            n =len (data )
            return sum (W ((x -x_i )/h )for x_i in data )/n
    else :
        sample =sorted (data )
        bandwidth =h *support
        def pdf (x ):
            nonlocal n ,sample
            if len (data )!=n :
                sample =sorted (data )
                n =len (data )
            i =bisect_left (sample ,x -bandwidth )
            j =bisect_right (sample ,x +bandwidth )
            supported =sample [i :j ]
            return sum (K ((x -x_i )/h )for x_i in supported )/(n *h )
        def cdf (x ):
            nonlocal n ,sample
            if len (data )!=n :
                sample =sorted (data )
                n =len (data )
            i =bisect_left (sample ,x -bandwidth )
            j =bisect_right (sample ,x +bandwidth )
            supported =sample [i :j ]
            return sum ((W ((x -x_i )/h )for x_i in supported ),i )/n
    if cumulative :
        cdf .__doc__ =f'CDF estimate with {h =!r } and {kernel =!r }'
        return cdf
    else :
        pdf .__doc__ =f'PDF estimate with {h =!r } and {kernel =!r }'
        return pdf
def quantiles (data ,*,n =4 ,method ='exclusive'):
    if n <1 :
        raise StatisticsError ('n must be at least 1')
    data =sorted (data )
    ld =len (data )
    if ld <2 :
        if ld ==1 :
            return data *(n -1 )
        raise StatisticsError ('must have at least one data point')
    if method =='inclusive':
        m =ld -1
        result =[]
        for i in range (1 ,n ):
            j ,delta =divmod (i *m ,n )
            interpolated =(data [j ]*(n -delta )+data [j +1 ]*delta )/n
            result .append (interpolated )
        return result
    if method =='exclusive':
        m =ld +1
        result =[]
        for i in range (1 ,n ):
            j =i *m //n
            j =1 if j <1 else ld -1 if j >ld -1 else j
            delta =i *m -j *n
            interpolated =(data [j -1 ]*(n -delta )+data [j ]*delta )/n
            result .append (interpolated )
        return result
    raise ValueError (f'Unknown method: {method !r }')
def variance (data ,xbar =None ):
    T ,ss ,c ,n =_ss (data ,xbar )
    if n <2 :
        raise StatisticsError ('variance requires at least two data points')
    return _convert (ss /(n -1 ),T )
def pvariance (data ,mu =None ):
    T ,ss ,c ,n =_ss (data ,mu )
    if n <1 :
        raise StatisticsError ('pvariance requires at least one data point')
    return _convert (ss /n ,T )
def stdev (data ,xbar =None ):
    T ,ss ,c ,n =_ss (data ,xbar )
    if n <2 :
        raise StatisticsError ('stdev requires at least two data points')
    mss =ss /(n -1 )
    try :
        mss_numerator =mss .numerator
        mss_denominator =mss .denominator
    except AttributeError :
        raise ValueError ('inf or nan encountered in data')
    if issubclass (T ,Decimal ):
        return _decimal_sqrt_of_frac (mss_numerator ,mss_denominator )
    return _float_sqrt_of_frac (mss_numerator ,mss_denominator )
def pstdev (data ,mu =None ):
    T ,ss ,c ,n =_ss (data ,mu )
    if n <1 :
        raise StatisticsError ('pstdev requires at least one data point')
    mss =ss /n
    try :
        mss_numerator =mss .numerator
        mss_denominator =mss .denominator
    except AttributeError :
        raise ValueError ('inf or nan encountered in data')
    if issubclass (T ,Decimal ):
        return _decimal_sqrt_of_frac (mss_numerator ,mss_denominator )
    return _float_sqrt_of_frac (mss_numerator ,mss_denominator )
def _mean_stdev (data ):
    T ,ss ,xbar ,n =_ss (data )
    if n <2 :
        raise StatisticsError ('stdev requires at least two data points')
    mss =ss /(n -1 )
    try :
        return float (xbar ),_float_sqrt_of_frac (mss .numerator ,mss .denominator )
    except AttributeError :
        return float (xbar ),float (xbar )/float (ss )
def _sqrtprod (x :float ,y :float )->float :
    h =sqrt (x *y )
    if not isfinite (h ):
        if isinf (h )and not isinf (x )and not isinf (y ):
            scale =2.0 **-512
            return _sqrtprod (scale *x ,scale *y )/scale
        return h
    if not h :
        if x and y :
            scale =2.0 **537
            return _sqrtprod (scale *x ,scale *y )/scale
        return h
    d =sumprod ((x ,h ),(y ,-h ))
    return h +d /(2.0 *h )
def covariance (x ,y ,/):
    n =len (x )
    if len (y )!=n :
        raise StatisticsError ('covariance requires that both inputs have same number of data points')
    if n <2 :
        raise StatisticsError ('covariance requires at least two data points')
    xbar =fsum (x )/n
    ybar =fsum (y )/n
    sxy =sumprod ((xi -xbar for xi in x ),(yi -ybar for yi in y ))
    return sxy /(n -1 )
def correlation (x ,y ,/,*,method ='linear'):
    n =len (x )
    if len (y )!=n :
        raise StatisticsError ('correlation requires that both inputs have same number of data points')
    if n <2 :
        raise StatisticsError ('correlation requires at least two data points')
    if method not in {'linear','ranked'}:
        raise ValueError (f'Unknown method: {method !r }')
    if method =='ranked':
        start =(n -1 )/-2
        x =_rank (x ,start =start )
        y =_rank (y ,start =start )
    else :
        xbar =fsum (x )/n
        ybar =fsum (y )/n
        x =[xi -xbar for xi in x ]
        y =[yi -ybar for yi in y ]
    sxy =sumprod (x ,y )
    sxx =sumprod (x ,x )
    syy =sumprod (y ,y )
    try :
        return sxy /_sqrtprod (sxx ,syy )
    except ZeroDivisionError :
        raise StatisticsError ('at least one of the inputs is constant')
LinearRegression =namedtuple ('LinearRegression',('slope','intercept'))
def linear_regression (x ,y ,/,*,proportional =False ):
    n =len (x )
    if len (y )!=n :
        raise StatisticsError ('linear regression requires that both inputs have same number of data points')
    if n <2 :
        raise StatisticsError ('linear regression requires at least two data points')
    if not proportional :
        xbar =fsum (x )/n
        ybar =fsum (y )/n
        x =[xi -xbar for xi in x ]
        y =(yi -ybar for yi in y )
    sxy =sumprod (x ,y )+0.0
    sxx =sumprod (x ,x )
    try :
        slope =sxy /sxx
    except ZeroDivisionError :
        raise StatisticsError ('x is constant')
    intercept =0.0 if proportional else ybar -slope *xbar
    return LinearRegression (slope =slope ,intercept =intercept )
def _normal_dist_inv_cdf (p ,mu ,sigma ):
    q =p -0.5
    if fabs (q )<=0.425 :
        r =0.180625 -q *q
        num =(((((((2.50908_09287_30122_6727e+3 *r +
        3.34305_75583_58812_8105e+4 )*r +
        6.72657_70927_00870_0853e+4 )*r +
        4.59219_53931_54987_1457e+4 )*r +
        1.37316_93765_50946_1125e+4 )*r +
        1.97159_09503_06551_4427e+3 )*r +
        1.33141_66789_17843_7745e+2 )*r +
        3.38713_28727_96366_6080e+0 )*q
        den =(((((((5.22649_52788_52854_5610e+3 *r +
        2.87290_85735_72194_2674e+4 )*r +
        3.93078_95800_09271_0610e+4 )*r +
        2.12137_94301_58659_5867e+4 )*r +
        5.39419_60214_24751_1077e+3 )*r +
        6.87187_00749_20579_0830e+2 )*r +
        4.23133_30701_60091_1252e+1 )*r +
        1.0 )
        x =num /den
        return mu +(x *sigma )
    r =p if q <=0.0 else 1.0 -p
    r =sqrt (-log (r ))
    if r <=5.0 :
        r =r -1.6
        num =(((((((7.74545_01427_83414_07640e-4 *r +
        2.27238_44989_26918_45833e-2 )*r +
        2.41780_72517_74506_11770e-1 )*r +
        1.27045_82524_52368_38258e+0 )*r +
        3.64784_83247_63204_60504e+0 )*r +
        5.76949_72214_60691_40550e+0 )*r +
        4.63033_78461_56545_29590e+0 )*r +
        1.42343_71107_49683_57734e+0 )
        den =(((((((1.05075_00716_44416_84324e-9 *r +
        5.47593_80849_95344_94600e-4 )*r +
        1.51986_66563_61645_71966e-2 )*r +
        1.48103_97642_74800_74590e-1 )*r +
        6.89767_33498_51000_04550e-1 )*r +
        1.67638_48301_83803_84940e+0 )*r +
        2.05319_16266_37758_82187e+0 )*r +
        1.0 )
    else :
        r =r -5.0
        num =(((((((2.01033_43992_92288_13265e-7 *r +
        2.71155_55687_43487_57815e-5 )*r +
        1.24266_09473_88078_43860e-3 )*r +
        2.65321_89526_57612_30930e-2 )*r +
        2.96560_57182_85048_91230e-1 )*r +
        1.78482_65399_17291_33580e+0 )*r +
        5.46378_49111_64114_36990e+0 )*r +
        6.65790_46435_01103_77720e+0 )
        den =(((((((2.04426_31033_89939_78564e-15 *r +
        1.42151_17583_16445_88870e-7 )*r +
        1.84631_83175_10054_68180e-5 )*r +
        7.86869_13114_56132_59100e-4 )*r +
        1.48753_61290_85061_48525e-2 )*r +
        1.36929_88092_27358_05310e-1 )*r +
        5.99832_20655_58879_37690e-1 )*r +
        1.0 )
    x =num /den
    if q <0.0 :
        x =-x
    return mu +(x *sigma )
try :
    from _statistics import _normal_dist_inv_cdf
except ImportError :
    pass
class NormalDist :
    __slots__ ={
    "":'Arithmetic mean of a normal distribution',
    "":'Standard deviation of a normal distribution',
    }
    def __init__ (self ,mu =0.0 ,sigma =1.0 ):
        if sigma <0.0 :
            raise StatisticsError ('sigma must be non-negative')
        self ._mu =float (mu )
        self ._sigma =float (sigma )
    @classmethod
    def from_samples (cls ,data ):
        return cls (*_mean_stdev (data ))
    def samples (self ,n ,*,seed =None ):
        rnd =random .random if seed is None else random .Random (seed ).random
        inv_cdf =_normal_dist_inv_cdf
        mu =self ._mu
        sigma =self ._sigma
        return [inv_cdf (rnd (),mu ,sigma )for _ in repeat (None ,n )]
    def pdf (self ,x ):
        variance =self ._sigma *self ._sigma
        if not variance :
            raise StatisticsError ('pdf() not defined when sigma is zero')
        diff =x -self ._mu
        return exp (diff *diff /(-2.0 *variance ))/sqrt (tau *variance )
    def cdf (self ,x ):
        if not self ._sigma :
            raise StatisticsError ('cdf() not defined when sigma is zero')
        return 0.5 *(1.0 +erf ((x -self ._mu )/(self ._sigma *_SQRT2 )))
    def inv_cdf (self ,p ):
        if p <=0.0 or p >=1.0 :
            raise StatisticsError ('p must be in the range 0.0 < p < 1.0')
        return _normal_dist_inv_cdf (p ,self ._mu ,self ._sigma )
    def quantiles (self ,n =4 ):
        return [self .inv_cdf (i /n )for i in range (1 ,n )]
    def overlap (self ,other ):
        if not isinstance (other ,NormalDist ):
            raise TypeError ('Expected another NormalDist instance')
        X ,Y =self ,other
        if (Y ._sigma ,Y ._mu )<(X ._sigma ,X ._mu ):
            X ,Y =Y ,X
        X_var ,Y_var =X .variance ,Y .variance
        if not X_var or not Y_var :
            raise StatisticsError ('overlap() not defined when sigma is zero')
        dv =Y_var -X_var
        dm =fabs (Y ._mu -X ._mu )
        if not dv :
            return 1.0 -erf (dm /(2.0 *X ._sigma *_SQRT2 ))
        a =X ._mu *Y_var -Y ._mu *X_var
        b =X ._sigma *Y ._sigma *sqrt (dm *dm +dv *log (Y_var /X_var ))
        x1 =(a +b )/dv
        x2 =(a -b )/dv
        return 1.0 -(fabs (Y .cdf (x1 )-X .cdf (x1 ))+fabs (Y .cdf (x2 )-X .cdf (x2 )))
    def zscore (self ,x ):
        if not self ._sigma :
            raise StatisticsError ('zscore() not defined when sigma is zero')
        return (x -self ._mu )/self ._sigma
    @property
    def mean (self ):
        return self ._mu
    @property
    def median (self ):
        return self ._mu
    @property
    def mode (self ):
        return self ._mu
    @property
    def stdev (self ):
        return self ._sigma
    @property
    def variance (self ):
        return self ._sigma *self ._sigma
    def __add__ (x1 ,x2 ):
        if isinstance (x2 ,NormalDist ):
            return NormalDist (x1 ._mu +x2 ._mu ,hypot (x1 ._sigma ,x2 ._sigma ))
        return NormalDist (x1 ._mu +x2 ,x1 ._sigma )
    def __sub__ (x1 ,x2 ):
        if isinstance (x2 ,NormalDist ):
            return NormalDist (x1 ._mu -x2 ._mu ,hypot (x1 ._sigma ,x2 ._sigma ))
        return NormalDist (x1 ._mu -x2 ,x1 ._sigma )
    def __mul__ (x1 ,x2 ):
        return NormalDist (x1 ._mu *x2 ,x1 ._sigma *fabs (x2 ))
    def __truediv__ (x1 ,x2 ):
        return NormalDist (x1 ._mu /x2 ,x1 ._sigma /fabs (x2 ))
    def __pos__ (x1 ):
        return NormalDist (x1 ._mu ,x1 ._sigma )
    def __neg__ (x1 ):
        return NormalDist (-x1 ._mu ,x1 ._sigma )
    __radd__ =__add__
    def __rsub__ (x1 ,x2 ):
        return -(x1 -x2 )
    __rmul__ =__mul__
    def __eq__ (x1 ,x2 ):
        if not isinstance (x2 ,NormalDist ):
            return NotImplemented
        return x1 ._mu ==x2 ._mu and x1 ._sigma ==x2 ._sigma
    def __hash__ (self ):
        return hash ((self ._mu ,self ._sigma ))
    def __repr__ (self ):
        return f'{type (self ).__name__ }(mu={self ._mu !r }, sigma={self ._sigma !r })'
    def __getstate__ (self ):
        return self ._mu ,self ._sigma
    def __setstate__ (self ,state ):
        self ._mu ,self ._sigma =state
def _newton_raphson (f_inv_estimate ,f ,f_prime ,tolerance =1e-12 ):
    def f_inv (y ):
        x =f_inv_estimate (y )
        while abs (diff :=f (x )-y )>tolerance :
            x -=diff /f_prime (x )
        return x
    return f_inv
def _quartic_invcdf_estimate (p ):
    sign ,p =(1.0 ,p )if p <=1 /2 else (-1.0 ,1.0 -p )
    x =(2.0 *p )**0.4258865685331 -1.0
    if p >=0.004 <0.499 :
        x +=0.026818732 *sin (7.101753784 *p +2.73230839482953 )
    return x *sign
_quartic_invcdf =_newton_raphson (
f_inv_estimate =_quartic_invcdf_estimate ,
f =lambda t :3 /16 *t **5 -5 /8 *t **3 +15 /16 *t +1 /2 ,
f_prime =lambda t :15 /16 *(1.0 -t *t )**2 )
def _triweight_invcdf_estimate (p ):
    sign ,p =(1.0 ,p )if p <=1 /2 else (-1.0 ,1.0 -p )
    x =(2.0 *p )**0.3400218741872791 -1.0
    return x *sign
_triweight_invcdf =_newton_raphson (
f_inv_estimate =_triweight_invcdf_estimate ,
f =lambda t :35 /32 *(-1 /7 *t **7 +3 /5 *t **5 -t **3 +t )+1 /2 ,
f_prime =lambda t :35 /32 *(1.0 -t *t )**3 )
_kernel_invcdfs ={
"":NormalDist ().inv_cdf ,
"":lambda p :log (p /(1 -p )),
"":lambda p :log (tan (p *pi /2 )),
"":lambda p :2 *p -1 ,
"":lambda p :2 *cos ((acos (2 *p -1 )+pi )/3 ),
"":_quartic_invcdf ,
"":_triweight_invcdf ,
"":lambda p :sqrt (2 *p )-1 if p <1 /2 else 1 -sqrt (2 -2 *p ),
"":lambda p :2 *asin (2 *p -1 )/pi ,
}
_kernel_invcdfs ['gauss']=_kernel_invcdfs ['normal']
_kernel_invcdfs ['uniform']=_kernel_invcdfs ['rectangular']
_kernel_invcdfs ['epanechnikov']=_kernel_invcdfs ['parabolic']
_kernel_invcdfs ['biweight']=_kernel_invcdfs ['quartic']
def kde_random (data ,h ,kernel ='normal',*,seed =None ):
    n =len (data )
    if not n :
        raise StatisticsError ('Empty data sequence')
    if not isinstance (data [0 ],(int ,float )):
        raise TypeError ('Data sequence must contain ints or floats')
    if h <=0.0 :
        raise StatisticsError (f'Bandwidth h must be positive, not {h =!r }')
    kernel_invcdf =_kernel_invcdfs .get (kernel )
    if kernel_invcdf is None :
        raise StatisticsError (f'Unknown kernel name: {kernel !r }')
    prng =_random .Random (seed )
    random =prng .random
    choice =prng .choice
    def rand ():
        return choice (data )+h *kernel_invcdf (random ())
    rand .__doc__ =f'Random KDE selection with {h =!r } and {kernel =!r }'
    return rand
