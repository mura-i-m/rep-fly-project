import contextlib
import os
import re
import fnmatch
import functools
import itertools
import operator
import stat
import sys
__all__ =["glob","iglob","escape","translate"]
def glob (pathname ,*,root_dir =None ,dir_fd =None ,recursive =False ,
include_hidden =False ):
    return list (iglob (pathname ,root_dir =root_dir ,dir_fd =dir_fd ,recursive =recursive ,
    include_hidden =include_hidden ))
def iglob (pathname ,*,root_dir =None ,dir_fd =None ,recursive =False ,
include_hidden =False ):
    sys .audit ("glob.glob",pathname ,recursive )
    sys .audit ("glob.glob/2",pathname ,recursive ,root_dir ,dir_fd )
    if root_dir is not None :
        root_dir =os .fspath (root_dir )
    else :
        root_dir =pathname [:0 ]
    it =_iglob (pathname ,root_dir ,dir_fd ,recursive ,False ,
    include_hidden =include_hidden )
    if not pathname or recursive and _isrecursive (pathname [:2 ]):
        try :
            s =next (it )
            if s :
                it =itertools .chain ((s ,),it )
        except StopIteration :
            pass
    return it
def _iglob (pathname ,root_dir ,dir_fd ,recursive ,dironly ,
include_hidden =False ):
    dirname ,basename =os .path .split (pathname )
    if not has_magic (pathname ):
        assert not dironly
        if basename :
            if _lexists (_join (root_dir ,pathname ),dir_fd ):
                yield pathname
        else :
            if _isdir (_join (root_dir ,dirname ),dir_fd ):
                yield pathname
        return
    if not dirname :
        if recursive and _isrecursive (basename ):
            yield from _glob2 (root_dir ,basename ,dir_fd ,dironly ,
            include_hidden =include_hidden )
        else :
            yield from _glob1 (root_dir ,basename ,dir_fd ,dironly ,
            include_hidden =include_hidden )
        return
    if dirname !=pathname and has_magic (dirname ):
        dirs =_iglob (dirname ,root_dir ,dir_fd ,recursive ,True ,
        include_hidden =include_hidden )
    else :
        dirs =[dirname ]
    if has_magic (basename ):
        if recursive and _isrecursive (basename ):
            glob_in_dir =_glob2
        else :
            glob_in_dir =_glob1
    else :
        glob_in_dir =_glob0
    for dirname in dirs :
        for name in glob_in_dir (_join (root_dir ,dirname ),basename ,dir_fd ,dironly ,
        include_hidden =include_hidden ):
            yield os .path .join (dirname ,name )
def _glob1 (dirname ,pattern ,dir_fd ,dironly ,include_hidden =False ):
    names =_listdir (dirname ,dir_fd ,dironly )
    if not (include_hidden or _ishidden (pattern )):
        names =(x for x in names if not _ishidden (x ))
    return fnmatch .filter (names ,pattern )
def _glob0 (dirname ,basename ,dir_fd ,dironly ,include_hidden =False ):
    if basename :
        if _lexists (_join (dirname ,basename ),dir_fd ):
            return [basename ]
    else :
        if _isdir (dirname ,dir_fd ):
            return [basename ]
    return []
_deprecated_function_message =(
)
def glob0 (dirname ,pattern ):
    import warnings
    warnings ._deprecated ("glob.glob0",_deprecated_function_message ,remove =(3 ,15 ))
    return _glob0 (dirname ,pattern ,None ,False )
def glob1 (dirname ,pattern ):
    import warnings
    warnings ._deprecated ("glob.glob1",_deprecated_function_message ,remove =(3 ,15 ))
    return _glob1 (dirname ,pattern ,None ,False )
def _glob2 (dirname ,pattern ,dir_fd ,dironly ,include_hidden =False ):
    assert _isrecursive (pattern )
    if not dirname or _isdir (dirname ,dir_fd ):
        yield pattern [:0 ]
    yield from _rlistdir (dirname ,dir_fd ,dironly ,
    include_hidden =include_hidden )
def _iterdir (dirname ,dir_fd ,dironly ):
    try :
        fd =None
        fsencode =None
        if dir_fd is not None :
            if dirname :
                fd =arg =os .open (dirname ,_dir_open_flags ,dir_fd =dir_fd )
            else :
                arg =dir_fd
            if isinstance (dirname ,bytes ):
                fsencode =os .fsencode
        elif dirname :
            arg =dirname
        elif isinstance (dirname ,bytes ):
            arg =bytes (os .curdir ,'ASCII')
        else :
            arg =os .curdir
        try :
            with os .scandir (arg )as it :
                for entry in it :
                    try :
                        if not dironly or entry .is_dir ():
                            if fsencode is not None :
                                yield fsencode (entry .name )
                            else :
                                yield entry .name
                    except OSError :
                        pass
        finally :
            if fd is not None :
                os .close (fd )
    except OSError :
        return
def _listdir (dirname ,dir_fd ,dironly ):
    with contextlib .closing (_iterdir (dirname ,dir_fd ,dironly ))as it :
        return list (it )
def _rlistdir (dirname ,dir_fd ,dironly ,include_hidden =False ):
    names =_listdir (dirname ,dir_fd ,dironly )
    for x in names :
        if include_hidden or not _ishidden (x ):
            yield x
            path =_join (dirname ,x )if dirname else x
            for y in _rlistdir (path ,dir_fd ,dironly ,
            include_hidden =include_hidden ):
                yield _join (x ,y )
def _lexists (pathname ,dir_fd ):
    if dir_fd is None :
        return os .path .lexists (pathname )
    try :
        os .lstat (pathname ,dir_fd =dir_fd )
    except (OSError ,ValueError ):
        return False
    else :
        return True
def _isdir (pathname ,dir_fd ):
    if dir_fd is None :
        return os .path .isdir (pathname )
    try :
        st =os .stat (pathname ,dir_fd =dir_fd )
    except (OSError ,ValueError ):
        return False
    else :
        return stat .S_ISDIR (st .st_mode )
def _join (dirname ,basename ):
    if not dirname or not basename :
        return dirname or basename
    return os .path .join (dirname ,basename )
magic_check =re .compile ('([*?[])')
magic_check_bytes =re .compile (b'([*?[])')
def has_magic (s ):
    if isinstance (s ,bytes ):
        match =magic_check_bytes .search (s )
    else :
        match =magic_check .search (s )
    return match is not None
def _ishidden (path ):
    return path [0 ]in ('.',b'.'[0 ])
def _isrecursive (pattern ):
    if isinstance (pattern ,bytes ):
        return pattern ==b'**'
    else :
        return pattern =='**'
def escape (pathname ):
    drive ,pathname =os .path .splitdrive (pathname )
    if isinstance (pathname ,bytes ):
        pathname =magic_check_bytes .sub (br'[\1]',pathname )
    else :
        pathname =magic_check .sub (r'[\1]',pathname )
    return drive +pathname
_special_parts =('','.','..')
_dir_open_flags =os .O_RDONLY |getattr (os ,'O_DIRECTORY',0 )
_no_recurse_symlinks =object ()
def translate (pat ,*,recursive =False ,include_hidden =False ,seps =None ):
    if not seps :
        if os .path .altsep :
            seps =(os .path .sep ,os .path .altsep )
        else :
            seps =os .path .sep
    escaped_seps =''.join (map (re .escape ,seps ))
    any_sep =f'[{escaped_seps }]'if len (seps )>1 else escaped_seps
    not_sep =f'[^{escaped_seps }]'
    if include_hidden :
        one_last_segment =f'{not_sep }+'
        one_segment =f'{one_last_segment }{any_sep }'
        any_segments =f'(?:.+{any_sep })?'
        any_last_segments ='.*'
    else :
        one_last_segment =f'[^{escaped_seps }.]{not_sep }*'
        one_segment =f'{one_last_segment }{any_sep }'
        any_segments =f'(?:{one_segment })*'
        any_last_segments =f'{any_segments }(?:{one_last_segment })?'
    results =[]
    parts =re .split (any_sep ,pat )
    last_part_idx =len (parts )-1
    for idx ,part in enumerate (parts ):
        if part =='*':
            results .append (one_segment if idx <last_part_idx else one_last_segment )
        elif recursive and part =='**':
            if idx <last_part_idx :
                if parts [idx +1 ]!='**':
                    results .append (any_segments )
            else :
                results .append (any_last_segments )
        else :
            if part :
                if not include_hidden and part [0 ]in '*?':
                    results .append (r'(?!\.)')
                results .extend (fnmatch ._translate (part ,f'{not_sep }*',not_sep ))
            if idx <last_part_idx :
                results .append (any_sep )
    res =''.join (results )
    return fr'(?s:{res })\Z'
@functools .lru_cache (maxsize =512 )
def _compile_pattern (pat ,sep ,case_sensitive ,recursive =True ):
    flags =re .NOFLAG if case_sensitive else re .IGNORECASE
    regex =translate (pat ,recursive =recursive ,include_hidden =True ,seps =sep )
    return re .compile (regex ,flags =flags ).match
class _Globber :
    def __init__ (self ,sep ,case_sensitive ,case_pedantic =False ,recursive =False ):
        self .sep =sep
        self .case_sensitive =case_sensitive
        self .case_pedantic =case_pedantic
        self .recursive =recursive
    lstat =operator .methodcaller ('lstat')
    add_slash =operator .methodcaller ('joinpath','')
    @staticmethod
    def scandir (path ):
        return contextlib .nullcontext (path .iterdir ())
    @staticmethod
    def concat_path (path ,text ):
        return path .with_segments (path ._raw_path +text )
    @staticmethod
    def parse_entry (entry ):
        return entry
    def compile (self ,pat ):
        return _compile_pattern (pat ,self .sep ,self .case_sensitive ,self .recursive )
    def selector (self ,parts ):
        if not parts :
            return self .select_exists
        part =parts .pop ()
        if self .recursive and part =='**':
            selector =self .recursive_selector
        elif part in _special_parts :
            selector =self .special_selector
        elif not self .case_pedantic and magic_check .search (part )is None :
            selector =self .literal_selector
        else :
            selector =self .wildcard_selector
        return selector (part ,parts )
    def special_selector (self ,part ,parts ):
        select_next =self .selector (parts )
        def select_special (path ,exists =False ):
            path =self .concat_path (self .add_slash (path ),part )
            return select_next (path ,exists )
        return select_special
    def literal_selector (self ,part ,parts ):
        while parts and magic_check .search (parts [-1 ])is None :
            part +=self .sep +parts .pop ()
        select_next =self .selector (parts )
        def select_literal (path ,exists =False ):
            path =self .concat_path (self .add_slash (path ),part )
            return select_next (path ,exists =False )
        return select_literal
    def wildcard_selector (self ,part ,parts ):
        match =None if part =='*'else self .compile (part )
        dir_only =bool (parts )
        if dir_only :
            select_next =self .selector (parts )
        def select_wildcard (path ,exists =False ):
            try :
                with self .scandir (path )as scandir_it :
                    entries =list (scandir_it )
            except OSError :
                pass
            else :
                for entry in entries :
                    if match is None or match (entry .name ):
                        if dir_only :
                            try :
                                if not entry .is_dir ():
                                    continue
                            except OSError :
                                continue
                        entry_path =self .parse_entry (entry )
                        if dir_only :
                            yield from select_next (entry_path ,exists =True )
                        else :
                            yield entry_path
        return select_wildcard
    def recursive_selector (self ,part ,parts ):
        while parts and parts [-1 ]=='**':
            parts .pop ()
        follow_symlinks =self .recursive is not _no_recurse_symlinks
        if follow_symlinks :
            while parts and parts [-1 ]not in _special_parts :
                part +=self .sep +parts .pop ()
        match =None if part =='**'else self .compile (part )
        dir_only =bool (parts )
        select_next =self .selector (parts )
        def select_recursive (path ,exists =False ):
            path =self .add_slash (path )
            match_pos =len (str (path ))
            if match is None or match (str (path ),match_pos ):
                yield from select_next (path ,exists )
            stack =[path ]
            while stack :
                yield from select_recursive_step (stack ,match_pos )
        def select_recursive_step (stack ,match_pos ):
            path =stack .pop ()
            try :
                with self .scandir (path )as scandir_it :
                    entries =list (scandir_it )
            except OSError :
                pass
            else :
                for entry in entries :
                    is_dir =False
                    try :
                        if entry .is_dir (follow_symlinks =follow_symlinks ):
                            is_dir =True
                    except OSError :
                        pass
                    if is_dir or not dir_only :
                        entry_path =self .parse_entry (entry )
                        if match is None or match (str (entry_path ),match_pos ):
                            if dir_only :
                                yield from select_next (entry_path ,exists =True )
                            else :
                                yield entry_path
                        if is_dir :
                            stack .append (entry_path )
        return select_recursive
    def select_exists (self ,path ,exists =False ):
        if exists :
            yield path
        else :
            try :
                self .lstat (path )
                yield path
            except OSError :
                pass
class _StringGlobber (_Globber ):
    lstat =staticmethod (os .lstat )
    scandir =staticmethod (os .scandir )
    parse_entry =operator .attrgetter ('path')
    concat_path =operator .add
    if os .name =='nt':
        @staticmethod
        def add_slash (pathname ):
            tail =os .path .splitroot (pathname )[2 ]
            if not tail or tail [-1 ]in '\\/':
                return pathname
            return f'{pathname }\\'
    else :
        @staticmethod
        def add_slash (pathname ):
            if not pathname or pathname [-1 ]=='/':
                return pathname
            return f'{pathname }/'
import os
import posixpath
import re
import functools
__all__ =["filter","fnmatch","fnmatchcase","translate"]
def fnmatch (name ,pat ):
    name =os .path .normcase (name )
    pat =os .path .normcase (pat )
    return fnmatchcase (name ,pat )
@functools .lru_cache (maxsize =32768 ,typed =True )
def _compile_pattern (pat ):
    if isinstance (pat ,bytes ):
        pat_str =str (pat ,'ISO-8859-1')
        res_str =translate (pat_str )
        res =bytes (res_str ,'ISO-8859-1')
    else :
        res =translate (pat )
    return re .compile (res ).match
def filter (names ,pat ):
    result =[]
    pat =os .path .normcase (pat )
    match =_compile_pattern (pat )
    if os .path is posixpath :
        for name in names :
            if match (name ):
                result .append (name )
    else :
        for name in names :
            if match (os .path .normcase (name )):
                result .append (name )
    return result
def fnmatchcase (name ,pat ):
    match =_compile_pattern (pat )
    return match (name )is not None
def translate (pat ):
    STAR =object ()
    parts =_translate (pat ,STAR ,'.')
    return _join_translated_parts (parts ,STAR )
def _translate (pat ,STAR ,QUESTION_MARK ):
    res =[]
    add =res .append
    i ,n =0 ,len (pat )
    while i <n :
        c =pat [i ]
        i =i +1
        if c =='*':
            if (not res )or res [-1 ]is not STAR :
                add (STAR )
        elif c =='?':
            add (QUESTION_MARK )
        elif c =='[':
            j =i
            if j <n and pat [j ]=='!':
                j =j +1
            if j <n and pat [j ]==']':
                j =j +1
            while j <n and pat [j ]!=']':
                j =j +1
            if j >=n :
                add ('\\[')
            else :
                stuff =pat [i :j ]
                if '-'not in stuff :
                    stuff =stuff .replace ('\\',r'\\')
                else :
                    chunks =[]
                    k =i +2 if pat [i ]=='!'else i +1
                    while True :
                        k =pat .find ('-',k ,j )
                        if k <0 :
                            break
                        chunks .append (pat [i :k ])
                        i =k +1
                        k =k +3
                    chunk =pat [i :j ]
                    if chunk :
                        chunks .append (chunk )
                    else :
                        chunks [-1 ]+='-'
                    for k in range (len (chunks )-1 ,0 ,-1 ):
                        if chunks [k -1 ][-1 ]>chunks [k ][0 ]:
                            chunks [k -1 ]=chunks [k -1 ][:-1 ]+chunks [k ][1 :]
                            del chunks [k ]
                    stuff ='-'.join (s .replace ('\\',r'\\').replace ('-',r'\-')
                    for s in chunks )
                stuff =re .sub (r'([&~|])',r'\\\1',stuff )
                i =j +1
                if not stuff :
                    add ('(?!)')
                elif stuff =='!':
                    add ('.')
                else :
                    if stuff [0 ]=='!':
                        stuff ='^'+stuff [1 :]
                    elif stuff [0 ]in ('^','['):
                        stuff ='\\'+stuff
                    add (f'[{stuff }]')
        else :
            add (re .escape (c ))
    assert i ==n
    return res
def _join_translated_parts (inp ,STAR ):
    res =[]
    add =res .append
    i ,n =0 ,len (inp )
    while i <n and inp [i ]is not STAR :
        add (inp [i ])
        i +=1
    while i <n :
        assert inp [i ]is STAR
        i +=1
        if i ==n :
            add (".*")
            break
        assert inp [i ]is not STAR
        fixed =[]
        while i <n and inp [i ]is not STAR :
            fixed .append (inp [i ])
            i +=1
        fixed ="".join (fixed )
        if i ==n :
            add (".*")
            add (fixed )
        else :
            add (f"(?>.*?{fixed })")
    assert i ==n
    res ="".join (res )
    return fr'(?s:{res })\Z'
import threading
import types
from collections import deque
from heapq import heappush ,heappop
from time import monotonic as time
try :
    from _queue import SimpleQueue
except ImportError :
    SimpleQueue =None
__all__ =[
"",
"",
"",
"",
"",
"",
"",
]
try :
    from _queue import Empty
except ImportError :
    class Empty (Exception ):
        pass
class Full (Exception ):
    pass
class ShutDown (Exception ):
class Queue :
    def __init__ (self ,maxsize =0 ):
        self .maxsize =maxsize
        self ._init (maxsize )
        self .mutex =threading .Lock ()
        self .not_empty =threading .Condition (self .mutex )
        self .not_full =threading .Condition (self .mutex )
        self .all_tasks_done =threading .Condition (self .mutex )
        self .unfinished_tasks =0
        self .is_shutdown =False
    def task_done (self ):
        with self .all_tasks_done :
            unfinished =self .unfinished_tasks -1
            if unfinished <=0 :
                if unfinished <0 :
                    raise ValueError ('task_done() called too many times')
                self .all_tasks_done .notify_all ()
            self .unfinished_tasks =unfinished
    def join (self ):
        with self .all_tasks_done :
            while self .unfinished_tasks :
                self .all_tasks_done .wait ()
    def qsize (self ):
        with self .mutex :
            return self ._qsize ()
    def empty (self ):
        with self .mutex :
            return not self ._qsize ()
    def full (self ):
        with self .mutex :
            return 0 <self .maxsize <=self ._qsize ()
    def put (self ,item ,block =True ,timeout =None ):
        with self .not_full :
            if self .is_shutdown :
                raise ShutDown
            if self .maxsize >0 :
                if not block :
                    if self ._qsize ()>=self .maxsize :
                        raise Full
                elif timeout is None :
                    while self ._qsize ()>=self .maxsize :
                        self .not_full .wait ()
                        if self .is_shutdown :
                            raise ShutDown
                elif timeout <0 :
                    raise ValueError ("'timeout' must be a non-negative number")
                else :
                    endtime =time ()+timeout
                    while self ._qsize ()>=self .maxsize :
                        remaining =endtime -time ()
                        if remaining <=0.0 :
                            raise Full
                        self .not_full .wait (remaining )
                        if self .is_shutdown :
                            raise ShutDown
            self ._put (item )
            self .unfinished_tasks +=1
            self .not_empty .notify ()
    def get (self ,block =True ,timeout =None ):
        with self .not_empty :
            if self .is_shutdown and not self ._qsize ():
                raise ShutDown
            if not block :
                if not self ._qsize ():
                    raise Empty
            elif timeout is None :
                while not self ._qsize ():
                    self .not_empty .wait ()
                    if self .is_shutdown and not self ._qsize ():
                        raise ShutDown
            elif timeout <0 :
                raise ValueError ("'timeout' must be a non-negative number")
            else :
                endtime =time ()+timeout
                while not self ._qsize ():
                    remaining =endtime -time ()
                    if remaining <=0.0 :
                        raise Empty
                    self .not_empty .wait (remaining )
                    if self .is_shutdown and not self ._qsize ():
                        raise ShutDown
            item =self ._get ()
            self .not_full .notify ()
            return item
    def put_nowait (self ,item ):
        return self .put (item ,block =False )
    def get_nowait (self ):
        return self .get (block =False )
    def shutdown (self ,immediate =False ):
        with self .mutex :
            self .is_shutdown =True
            if immediate :
                while self ._qsize ():
                    self ._get ()
                    if self .unfinished_tasks >0 :
                        self .unfinished_tasks -=1
                self .all_tasks_done .notify_all ()
            self .not_empty .notify_all ()
            self .not_full .notify_all ()
    def _init (self ,maxsize ):
        self .queue =deque ()
    def _qsize (self ):
        return len (self .queue )
    def _put (self ,item ):
        self .queue .append (item )
    def _get (self ):
        return self .queue .popleft ()
    __class_getitem__ =classmethod (types .GenericAlias )
class PriorityQueue (Queue ):
    def _init (self ,maxsize ):
        self .queue =[]
    def _qsize (self ):
        return len (self .queue )
    def _put (self ,item ):
        heappush (self .queue ,item )
    def _get (self ):
        return heappop (self .queue )
class LifoQueue (Queue ):
    def _init (self ,maxsize ):
        self .queue =[]
    def _qsize (self ):
        return len (self .queue )
    def _put (self ,item ):
        self .queue .append (item )
    def _get (self ):
        return self .queue .pop ()
class _PySimpleQueue :
    def __init__ (self ):
        self ._queue =deque ()
        self ._count =threading .Semaphore (0 )
    def put (self ,item ,block =True ,timeout =None ):
        self ._queue .append (item )
        self ._count .release ()
    def get (self ,block =True ,timeout =None ):
        if not block :
            timeout =None
        elif timeout is not None and timeout <0 :
            raise ValueError ("'timeout' must be a non-negative number")
        if not self ._count .acquire (block ,timeout ):
            raise Empty
        return self ._queue .popleft ()
    def put_nowait (self ,item ):
        return self .put (item ,block =False )
    def get_nowait (self ):
        return self .get (block =False )
    def empty (self ):
        return len (self ._queue )==0
    def qsize (self ):
        return len (self ._queue )
    __class_getitem__ =classmethod (types .GenericAlias )
if SimpleQueue is None :
    SimpleQueue =_PySimpleQueue
__all__ =["rgb_to_yiq","yiq_to_rgb","rgb_to_hls","hls_to_rgb",
"","hsv_to_rgb"]
ONE_THIRD =1.0 /3.0
ONE_SIXTH =1.0 /6.0
TWO_THIRD =2.0 /3.0
def rgb_to_yiq (r ,g ,b ):
    y =0.30 *r +0.59 *g +0.11 *b
    i =0.74 *(r -y )-0.27 *(b -y )
    q =0.48 *(r -y )+0.41 *(b -y )
    return (y ,i ,q )
def yiq_to_rgb (y ,i ,q ):
    r =y +0.9468822170900693 *i +0.6235565819861433 *q
    g =y -0.27478764629897834 *i -0.6356910791873801 *q
    b =y -1.1085450346420322 *i +1.7090069284064666 *q
    if r <0.0 :
        r =0.0
    if g <0.0 :
        g =0.0
    if b <0.0 :
        b =0.0
    if r >1.0 :
        r =1.0
    if g >1.0 :
        g =1.0
    if b >1.0 :
        b =1.0
    return (r ,g ,b )
def rgb_to_hls (r ,g ,b ):
    maxc =max (r ,g ,b )
    minc =min (r ,g ,b )
    sumc =(maxc +minc )
    rangec =(maxc -minc )
    l =sumc /2.0
    if minc ==maxc :
        return 0.0 ,l ,0.0
    if l <=0.5 :
        s =rangec /sumc
    else :
        s =rangec /(2.0 -maxc -minc )
    rc =(maxc -r )/rangec
    gc =(maxc -g )/rangec
    bc =(maxc -b )/rangec
    if r ==maxc :
        h =bc -gc
    elif g ==maxc :
        h =2.0 +rc -bc
    else :
        h =4.0 +gc -rc
    h =(h /6.0 )%1.0
    return h ,l ,s
def hls_to_rgb (h ,l ,s ):
    if s ==0.0 :
        return l ,l ,l
    if l <=0.5 :
        m2 =l *(1.0 +s )
    else :
        m2 =l +s -(l *s )
    m1 =2.0 *l -m2
    return (_v (m1 ,m2 ,h +ONE_THIRD ),_v (m1 ,m2 ,h ),_v (m1 ,m2 ,h -ONE_THIRD ))
def _v (m1 ,m2 ,hue ):
    hue =hue %1.0
    if hue <ONE_SIXTH :
        return m1 +(m2 -m1 )*hue *6.0
    if hue <0.5 :
        return m2
    if hue <TWO_THIRD :
        return m1 +(m2 -m1 )*(TWO_THIRD -hue )*6.0
    return m1
def rgb_to_hsv (r ,g ,b ):
    maxc =max (r ,g ,b )
    minc =min (r ,g ,b )
    rangec =(maxc -minc )
    v =maxc
    if minc ==maxc :
        return 0.0 ,0.0 ,v
    s =rangec /maxc
    rc =(maxc -r )/rangec
    gc =(maxc -g )/rangec
    bc =(maxc -b )/rangec
    if r ==maxc :
        h =bc -gc
    elif g ==maxc :
        h =2.0 +rc -bc
    else :
        h =4.0 +gc -rc
    h =(h /6.0 )%1.0
    return h ,s ,v
def hsv_to_rgb (h ,s ,v ):
    if s ==0.0 :
        return v ,v ,v
    i =int (h *6.0 )
    f =(h *6.0 )-i
    p =v *(1.0 -s )
    q =v *(1.0 -s *f )
    t =v *(1.0 -s *(1.0 -f ))
    i =i %6
    if i ==0 :
        return v ,t ,p
    if i ==1 :
        return q ,v ,p
    if i ==2 :
        return p ,v ,t
    if i ==3 :
        return p ,q ,v
    if i ==4 :
        return t ,p ,v
    if i ==5 :
        return v ,p ,q
__version__ ='1.1'
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
]
import os as _os
import re as _re
import sys as _sys
from gettext import gettext as _ ,ngettext
SUPPRESS ='==SUPPRESS=='
OPTIONAL ='?'
ZERO_OR_MORE ='*'
ONE_OR_MORE ='+'
PARSER ='A...'
REMAINDER ='...'
_UNRECOGNIZED_ARGS_ATTR ='_unrecognized_args'
class _AttributeHolder (object ):
    def __repr__ (self ):
        type_name =type (self ).__name__
        arg_strings =[]
        star_args ={}
        for arg in self ._get_args ():
            arg_strings .append (repr (arg ))
        for name ,value in self ._get_kwargs ():
            if name .isidentifier ():
                arg_strings .append ('%s=%r'%(name ,value ))
            else :
                star_args [name ]=value
        if star_args :
            arg_strings .append ('**%s'%repr (star_args ))
        return '%s(%s)'%(type_name ,', '.join (arg_strings ))
    def _get_kwargs (self ):
        return list (self .__dict__ .items ())
    def _get_args (self ):
        return []
def _copy_items (items ):
    if items is None :
        return []
    if type (items )is list :
        return items [:]
    import copy
    return copy .copy (items )
class HelpFormatter (object ):
    def __init__ (self ,
    prog ,
    indent_increment =2 ,
    max_help_position =24 ,
    width =None ):
        if width is None :
            import shutil
            width =shutil .get_terminal_size ().columns
            width -=2
        self ._prog =prog
        self ._indent_increment =indent_increment
        self ._max_help_position =min (max_help_position ,
        max (width -20 ,indent_increment *2 ))
        self ._width =width
        self ._current_indent =0
        self ._level =0
        self ._action_max_length =0
        self ._root_section =self ._Section (self ,None )
        self ._current_section =self ._root_section
        self ._whitespace_matcher =_re .compile (r'\s+',_re .ASCII )
        self ._long_break_matcher =_re .compile (r'\n\n\n+')
    def _indent (self ):
        self ._current_indent +=self ._indent_increment
        self ._level +=1
    def _dedent (self ):
        self ._current_indent -=self ._indent_increment
        assert self ._current_indent >=0 ,'Indent decreased below 0.'
        self ._level -=1
    class _Section (object ):
        def __init__ (self ,formatter ,parent ,heading =None ):
            self .formatter =formatter
            self .parent =parent
            self .heading =heading
            self .items =[]
        def format_help (self ):
            if self .parent is not None :
                self .formatter ._indent ()
            join =self .formatter ._join_parts
            item_help =join ([func (*args )for func ,args in self .items ])
            if self .parent is not None :
                self .formatter ._dedent ()
            if not item_help :
                return ''
            if self .heading is not SUPPRESS and self .heading is not None :
                current_indent =self .formatter ._current_indent
                heading_text =_ ('%(heading)s:')%dict (heading =self .heading )
                heading ='%*s%s\n'%(current_indent ,'',heading_text )
            else :
                heading =''
            return join (['\n',heading ,item_help ,'\n'])
    def _add_item (self ,func ,args ):
        self ._current_section .items .append ((func ,args ))
    def start_section (self ,heading ):
        self ._indent ()
        section =self ._Section (self ,self ._current_section ,heading )
        self ._add_item (section .format_help ,[])
        self ._current_section =section
    def end_section (self ):
        self ._current_section =self ._current_section .parent
        self ._dedent ()
    def add_text (self ,text ):
        if text is not SUPPRESS and text is not None :
            self ._add_item (self ._format_text ,[text ])
    def add_usage (self ,usage ,actions ,groups ,prefix =None ):
        if usage is not SUPPRESS :
            args =usage ,actions ,groups ,prefix
            self ._add_item (self ._format_usage ,args )
    def add_argument (self ,action ):
        if action .help is not SUPPRESS :
            get_invocation =self ._format_action_invocation
            invocation_lengths =[len (get_invocation (action ))+self ._current_indent ]
            for subaction in self ._iter_indented_subactions (action ):
                invocation_lengths .append (len (get_invocation (subaction ))+self ._current_indent )
            action_length =max (invocation_lengths )
            self ._action_max_length =max (self ._action_max_length ,
            action_length )
            self ._add_item (self ._format_action ,[action ])
    def add_arguments (self ,actions ):
        for action in actions :
            self .add_argument (action )
    def format_help (self ):
        help =self ._root_section .format_help ()
        if help :
            help =self ._long_break_matcher .sub ('\n\n',help )
            help =help .strip ('\n')+'\n'
        return help
    def _join_parts (self ,part_strings ):
        return ''.join ([part
        for part in part_strings
        if part and part is not SUPPRESS ])
    def _format_usage (self ,usage ,actions ,groups ,prefix ):
        if prefix is None :
            prefix =_ ('usage: ')
        if usage is not None :
            usage =usage %dict (prog =self ._prog )
        elif usage is None and not actions :
            usage ='%(prog)s'%dict (prog =self ._prog )
        elif usage is None :
            prog ='%(prog)s'%dict (prog =self ._prog )
            optionals =[]
            positionals =[]
            for action in actions :
                if action .option_strings :
                    optionals .append (action )
                else :
                    positionals .append (action )
            format =self ._format_actions_usage
            action_usage =format (optionals +positionals ,groups )
            usage =' '.join ([s for s in [prog ,action_usage ]if s ])
            text_width =self ._width -self ._current_indent
            if len (prefix )+len (usage )>text_width :
                all_actions =optionals +positionals
                parts ,pos_start =self ._get_actions_usage_parts_with_split (
                all_actions ,groups ,len (optionals )
                )
                opt_parts =parts [:pos_start ]
                pos_parts =parts [pos_start :]
                def get_lines (parts ,indent ,prefix =None ):
                    lines =[]
                    line =[]
                    indent_length =len (indent )
                    if prefix is not None :
                        line_len =len (prefix )-1
                    else :
                        line_len =indent_length -1
                    for part in parts :
                        if line_len +1 +len (part )>text_width and line :
                            lines .append (indent +' '.join (line ))
                            line =[]
                            line_len =indent_length -1
                        line .append (part )
                        line_len +=len (part )+1
                    if line :
                        lines .append (indent +' '.join (line ))
                    if prefix is not None :
                        lines [0 ]=lines [0 ][indent_length :]
                    return lines
                if len (prefix )+len (prog )<=0.75 *text_width :
                    indent =' '*(len (prefix )+len (prog )+1 )
                    if opt_parts :
                        lines =get_lines ([prog ]+opt_parts ,indent ,prefix )
                        lines .extend (get_lines (pos_parts ,indent ))
                    elif pos_parts :
                        lines =get_lines ([prog ]+pos_parts ,indent ,prefix )
                    else :
                        lines =[prog ]
                else :
                    indent =' '*len (prefix )
                    parts =opt_parts +pos_parts
                    lines =get_lines (parts ,indent )
                    if len (lines )>1 :
                        lines =[]
                        lines .extend (get_lines (opt_parts ,indent ))
                        lines .extend (get_lines (pos_parts ,indent ))
                    lines =[prog ]+lines
                usage ='\n'.join (lines )
        return '%s%s\n\n'%(prefix ,usage )
    def _format_actions_usage (self ,actions ,groups ):
        return ' '.join (self ._get_actions_usage_parts (actions ,groups ))
    def _get_actions_usage_parts (self ,actions ,groups ):
        parts ,_ =self ._get_actions_usage_parts_with_split (actions ,groups )
        return parts
    def _get_actions_usage_parts_with_split (self ,actions ,groups ,opt_count =None ):
        group_actions =set ()
        inserts ={}
        for group in groups :
            if not group ._group_actions :
                raise ValueError (f'empty group {group }')
            if all (action .help is SUPPRESS for action in group ._group_actions ):
                continue
            try :
                start =actions .index (group ._group_actions [0 ])
            except ValueError :
                continue
            else :
                end =start +len (group ._group_actions )
                if actions [start :end ]==group ._group_actions :
                    group_actions .update (group ._group_actions )
                    inserts [start ,end ]=group
        parts =[]
        for action in actions :
            if action .help is SUPPRESS :
                part =None
            elif not action .option_strings :
                default =self ._get_default_metavar_for_positional (action )
                part =self ._format_args (action ,default )
                if action in group_actions :
                    if part [0 ]=='['and part [-1 ]==']':
                        part =part [1 :-1 ]
            else :
                option_string =action .option_strings [0 ]
                if action .nargs ==0 :
                    part =action .format_usage ()
                else :
                    default =self ._get_default_metavar_for_optional (action )
                    args_string =self ._format_args (action ,default )
                    part ='%s %s'%(option_string ,args_string )
                if not action .required and action not in group_actions :
                    part ='[%s]'%part
            parts .append (part )
        inserted_separators_indices =set ()
        for start ,end in sorted (inserts ,reverse =True ):
            group =inserts [start ,end ]
            group_parts =[item for item in parts [start :end ]if item is not None ]
            group_size =len (group_parts )
            if group .required :
                open ,close ="()"if group_size >1 else ("","")
            else :
                open ,close ="[]"
            group_parts [0 ]=open +group_parts [0 ]
            group_parts [-1 ]=group_parts [-1 ]+close
            for i ,part in enumerate (group_parts [:-1 ],start =start ):
                if i not in inserted_separators_indices :
                    parts [i ]=part +' |'
                    inserted_separators_indices .add (i )
            parts [start +group_size -1 ]=group_parts [-1 ]
            for i in range (start +group_size ,end ):
                parts [i ]=None
        if opt_count is not None :
            pos_start =sum (1 for p in parts [:opt_count ]if p is not None )
        else :
            pos_start =None
        return [item for item in parts if item is not None ],pos_start
    def _format_text (self ,text ):
        if '%(prog)'in text :
            text =text %dict (prog =self ._prog )
        text_width =max (self ._width -self ._current_indent ,11 )
        indent =' '*self ._current_indent
        return self ._fill_text (text ,text_width ,indent )+'\n\n'
    def _format_action (self ,action ):
        help_position =min (self ._action_max_length +2 ,
        self ._max_help_position )
        help_width =max (self ._width -help_position ,11 )
        action_width =help_position -self ._current_indent -2
        action_header =self ._format_action_invocation (action )
        if not action .help :
            tup =self ._current_indent ,'',action_header
            action_header ='%*s%s\n'%tup
        elif len (action_header )<=action_width :
            tup =self ._current_indent ,'',action_width ,action_header
            action_header ='%*s%-*s  '%tup
            indent_first =0
        else :
            tup =self ._current_indent ,'',action_header
            action_header ='%*s%s\n'%tup
            indent_first =help_position
        parts =[action_header ]
        if action .help and action .help .strip ():
            help_text =self ._expand_help (action )
            if help_text :
                help_lines =self ._split_lines (help_text ,help_width )
                parts .append ('%*s%s\n'%(indent_first ,'',help_lines [0 ]))
                for line in help_lines [1 :]:
                    parts .append ('%*s%s\n'%(help_position ,'',line ))
        elif not action_header .endswith ('\n'):
            parts .append ('\n')
        for subaction in self ._iter_indented_subactions (action ):
            parts .append (self ._format_action (subaction ))
        return self ._join_parts (parts )
    def _format_action_invocation (self ,action ):
        if not action .option_strings :
            default =self ._get_default_metavar_for_positional (action )
            return ' '.join (self ._metavar_formatter (action ,default )(1 ))
        else :
            if action .nargs ==0 :
                return ', '.join (action .option_strings )
            else :
                default =self ._get_default_metavar_for_optional (action )
                args_string =self ._format_args (action ,default )
                return ', '.join (action .option_strings )+' '+args_string
    def _metavar_formatter (self ,action ,default_metavar ):
        if action .metavar is not None :
            result =action .metavar
        elif action .choices is not None :
            result ='{%s}'%','.join (map (str ,action .choices ))
        else :
            result =default_metavar
        def format (tuple_size ):
            if isinstance (result ,tuple ):
                return result
            else :
                return (result ,)*tuple_size
        return format
    def _format_args (self ,action ,default_metavar ):
        get_metavar =self ._metavar_formatter (action ,default_metavar )
        if action .nargs is None :
            result ='%s'%get_metavar (1 )
        elif action .nargs ==OPTIONAL :
            result ='[%s]'%get_metavar (1 )
        elif action .nargs ==ZERO_OR_MORE :
            metavar =get_metavar (1 )
            if len (metavar )==2 :
                result ='[%s [%s ...]]'%metavar
            else :
                result ='[%s ...]'%metavar
        elif action .nargs ==ONE_OR_MORE :
            result ='%s [%s ...]'%get_metavar (2 )
        elif action .nargs ==REMAINDER :
            result ='...'
        elif action .nargs ==PARSER :
            result ='%s ...'%get_metavar (1 )
        elif action .nargs ==SUPPRESS :
            result =''
        else :
            try :
                formats =['%s'for _ in range (action .nargs )]
            except TypeError :
                raise ValueError ("invalid nargs value")from None
            result =' '.join (formats )%get_metavar (action .nargs )
        return result
    def _expand_help (self ,action ):
        params =dict (vars (action ),prog =self ._prog )
        for name in list (params ):
            if params [name ]is SUPPRESS :
                del params [name ]
        for name in list (params ):
            if hasattr (params [name ],'__name__'):
                params [name ]=params [name ].__name__
        if params .get ('choices')is not None :
            params ['choices']=', '.join (map (str ,params ['choices']))
        return self ._get_help_string (action )%params
    def _iter_indented_subactions (self ,action ):
        try :
            get_subactions =action ._get_subactions
        except AttributeError :
            pass
        else :
            self ._indent ()
            yield from get_subactions ()
            self ._dedent ()
    def _split_lines (self ,text ,width ):
        text =self ._whitespace_matcher .sub (' ',text ).strip ()
        import textwrap
        return textwrap .wrap (text ,width )
    def _fill_text (self ,text ,width ,indent ):
        text =self ._whitespace_matcher .sub (' ',text ).strip ()
        import textwrap
        return textwrap .fill (text ,width ,
        initial_indent =indent ,
        subsequent_indent =indent )
    def _get_help_string (self ,action ):
        return action .help
    def _get_default_metavar_for_optional (self ,action ):
        return action .dest .upper ()
    def _get_default_metavar_for_positional (self ,action ):
        return action .dest
class RawDescriptionHelpFormatter (HelpFormatter ):
    def _fill_text (self ,text ,width ,indent ):
        return ''.join (indent +line for line in text .splitlines (keepends =True ))
class RawTextHelpFormatter (RawDescriptionHelpFormatter ):
    def _split_lines (self ,text ,width ):
        return text .splitlines ()
class ArgumentDefaultsHelpFormatter (HelpFormatter ):
    def _get_help_string (self ,action ):
        help =action .help
        if help is None :
            help =''
        if (
        ""not in help
        and action .default is not SUPPRESS
        and not action .required
        ):
            defaulting_nargs =(OPTIONAL ,ZERO_OR_MORE )
            if action .option_strings or action .nargs in defaulting_nargs :
                help +=_ (' (default: %(default)s)')
        return help
class MetavarTypeHelpFormatter (HelpFormatter ):
    def _get_default_metavar_for_optional (self ,action ):
        return action .type .__name__
    def _get_default_metavar_for_positional (self ,action ):
        return action .type .__name__
def _get_action_name (argument ):
    if argument is None :
        return None
    elif argument .option_strings :
        return '/'.join (argument .option_strings )
    elif argument .metavar not in (None ,SUPPRESS ):
        metavar =argument .metavar
        if not isinstance (metavar ,tuple ):
            return metavar
        if argument .nargs ==ZERO_OR_MORE and len (metavar )==2 :
            return '%s[, %s]'%metavar
        elif argument .nargs ==ONE_OR_MORE :
            return '%s[, %s]'%metavar
        else :
            return ', '.join (metavar )
    elif argument .dest not in (None ,SUPPRESS ):
        return argument .dest
    elif argument .choices :
        return '{%s}'%','.join (map (str ,argument .choices ))
    else :
        return None
class ArgumentError (Exception ):
    def __init__ (self ,argument ,message ):
        self .argument_name =_get_action_name (argument )
        self .message =message
    def __str__ (self ):
        if self .argument_name is None :
            format ='%(message)s'
        else :
            format =_ ('argument %(argument_name)s: %(message)s')
        return format %dict (message =self .message ,
        argument_name =self .argument_name )
class ArgumentTypeError (Exception ):
    pass
class Action (_AttributeHolder ):
    def __init__ (self ,
    option_strings ,
    dest ,
    nargs =None ,
    const =None ,
    default =None ,
    type =None ,
    choices =None ,
    required =False ,
    help =None ,
    metavar =None ,
    deprecated =False ):
        self .option_strings =option_strings
        self .dest =dest
        self .nargs =nargs
        self .const =const
        self .default =default
        self .type =type
        self .choices =choices
        self .required =required
        self .help =help
        self .metavar =metavar
        self .deprecated =deprecated
    def _get_kwargs (self ):
        names =[
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
        return [(name ,getattr (self ,name ))for name in names ]
    def format_usage (self ):
        return self .option_strings [0 ]
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        raise NotImplementedError (_ ('.__call__() not defined'))
_deprecated_default =object ()
class BooleanOptionalAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest ,
    default =None ,
    type =_deprecated_default ,
    choices =_deprecated_default ,
    required =False ,
    help =None ,
    metavar =_deprecated_default ,
    deprecated =False ):
        _option_strings =[]
        for option_string in option_strings :
            _option_strings .append (option_string )
            if option_string .startswith ('--'):
                option_string ='--no-'+option_string [2 :]
                _option_strings .append (option_string )
        for field_name in ('type','choices','metavar'):
            if locals ()[field_name ]is not _deprecated_default :
                import warnings
                warnings ._deprecated (
                field_name ,
                "",
                remove =(3 ,14 ))
        if type is _deprecated_default :
            type =None
        if choices is _deprecated_default :
            choices =None
        if metavar is _deprecated_default :
            metavar =None
        super ().__init__ (
        option_strings =_option_strings ,
        dest =dest ,
        nargs =0 ,
        default =default ,
        type =type ,
        choices =choices ,
        required =required ,
        help =help ,
        metavar =metavar ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        if option_string in self .option_strings :
            setattr (namespace ,self .dest ,not option_string .startswith ('--no-'))
    def format_usage (self ):
        return ' | '.join (self .option_strings )
class _StoreAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest ,
    nargs =None ,
    const =None ,
    default =None ,
    type =None ,
    choices =None ,
    required =False ,
    help =None ,
    metavar =None ,
    deprecated =False ):
        if nargs ==0 :
            raise ValueError ('nargs for store actions must be != 0; if you '
            "")
        if const is not None and nargs !=OPTIONAL :
            raise ValueError ('nargs must be %r to supply const'%OPTIONAL )
        super (_StoreAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        nargs =nargs ,
        const =const ,
        default =default ,
        type =type ,
        choices =choices ,
        required =required ,
        help =help ,
        metavar =metavar ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        setattr (namespace ,self .dest ,values )
class _StoreConstAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest ,
    const =None ,
    default =None ,
    required =False ,
    help =None ,
    metavar =None ,
    deprecated =False ):
        super (_StoreConstAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        nargs =0 ,
        const =const ,
        default =default ,
        required =required ,
        help =help ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        setattr (namespace ,self .dest ,self .const )
class _StoreTrueAction (_StoreConstAction ):
    def __init__ (self ,
    option_strings ,
    dest ,
    default =False ,
    required =False ,
    help =None ,
    deprecated =False ):
        super (_StoreTrueAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        const =True ,
        deprecated =deprecated ,
        required =required ,
        help =help ,
        default =default )
class _StoreFalseAction (_StoreConstAction ):
    def __init__ (self ,
    option_strings ,
    dest ,
    default =True ,
    required =False ,
    help =None ,
    deprecated =False ):
        super (_StoreFalseAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        const =False ,
        default =default ,
        required =required ,
        help =help ,
        deprecated =deprecated )
class _AppendAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest ,
    nargs =None ,
    const =None ,
    default =None ,
    type =None ,
    choices =None ,
    required =False ,
    help =None ,
    metavar =None ,
    deprecated =False ):
        if nargs ==0 :
            raise ValueError ('nargs for append actions must be != 0; if arg '
            "")
        if const is not None and nargs !=OPTIONAL :
            raise ValueError ('nargs must be %r to supply const'%OPTIONAL )
        super (_AppendAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        nargs =nargs ,
        const =const ,
        default =default ,
        type =type ,
        choices =choices ,
        required =required ,
        help =help ,
        metavar =metavar ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        items =getattr (namespace ,self .dest ,None )
        items =_copy_items (items )
        items .append (values )
        setattr (namespace ,self .dest ,items )
class _AppendConstAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest ,
    const =None ,
    default =None ,
    required =False ,
    help =None ,
    metavar =None ,
    deprecated =False ):
        super (_AppendConstAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        nargs =0 ,
        const =const ,
        default =default ,
        required =required ,
        help =help ,
        metavar =metavar ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        items =getattr (namespace ,self .dest ,None )
        items =_copy_items (items )
        items .append (self .const )
        setattr (namespace ,self .dest ,items )
class _CountAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest ,
    default =None ,
    required =False ,
    help =None ,
    deprecated =False ):
        super (_CountAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        nargs =0 ,
        default =default ,
        required =required ,
        help =help ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        count =getattr (namespace ,self .dest ,None )
        if count is None :
            count =0
        setattr (namespace ,self .dest ,count +1 )
class _HelpAction (Action ):
    def __init__ (self ,
    option_strings ,
    dest =SUPPRESS ,
    default =SUPPRESS ,
    help =None ,
    deprecated =False ):
        super (_HelpAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        default =default ,
        nargs =0 ,
        help =help ,
        deprecated =deprecated )
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        parser .print_help ()
        parser .exit ()
class _VersionAction (Action ):
    def __init__ (self ,
    option_strings ,
    version =None ,
    dest =SUPPRESS ,
    default =SUPPRESS ,
    help =None ,
    deprecated =False ):
        if help is None :
            help =_ ("show program's version number and exit")
        super (_VersionAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        default =default ,
        nargs =0 ,
        help =help )
        self .version =version
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        version =self .version
        if version is None :
            version =parser .version
        formatter =parser ._get_formatter ()
        formatter .add_text (version )
        parser ._print_message (formatter .format_help (),_sys .stdout )
        parser .exit ()
class _SubParsersAction (Action ):
    class _ChoicesPseudoAction (Action ):
        def __init__ (self ,name ,aliases ,help ):
            metavar =dest =name
            if aliases :
                metavar +=' (%s)'%', '.join (aliases )
            sup =super (_SubParsersAction ._ChoicesPseudoAction ,self )
            sup .__init__ (option_strings =[],dest =dest ,help =help ,
            metavar =metavar )
    def __init__ (self ,
    option_strings ,
    prog ,
    parser_class ,
    dest =SUPPRESS ,
    required =False ,
    help =None ,
    metavar =None ):
        self ._prog_prefix =prog
        self ._parser_class =parser_class
        self ._name_parser_map ={}
        self ._choices_actions =[]
        self ._deprecated =set ()
        super (_SubParsersAction ,self ).__init__ (
        option_strings =option_strings ,
        dest =dest ,
        nargs =PARSER ,
        choices =self ._name_parser_map ,
        required =required ,
        help =help ,
        metavar =metavar )
    def add_parser (self ,name ,*,deprecated =False ,**kwargs ):
        if kwargs .get ('prog')is None :
            kwargs ['prog']='%s %s'%(self ._prog_prefix ,name )
        aliases =kwargs .pop ('aliases',())
        if name in self ._name_parser_map :
            raise ArgumentError (self ,_ ('conflicting subparser: %s')%name )
        for alias in aliases :
            if alias in self ._name_parser_map :
                raise ArgumentError (
                self ,_ ('conflicting subparser alias: %s')%alias )
        if 'help'in kwargs :
            help =kwargs .pop ('help')
            choice_action =self ._ChoicesPseudoAction (name ,aliases ,help )
            self ._choices_actions .append (choice_action )
        parser =self ._parser_class (**kwargs )
        self ._name_parser_map [name ]=parser
        for alias in aliases :
            self ._name_parser_map [alias ]=parser
        if deprecated :
            self ._deprecated .add (name )
            self ._deprecated .update (aliases )
        return parser
    def _get_subactions (self ):
        return self ._choices_actions
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        parser_name =values [0 ]
        arg_strings =values [1 :]
        if self .dest is not SUPPRESS :
            setattr (namespace ,self .dest ,parser_name )
        try :
            subparser =self ._name_parser_map [parser_name ]
        except KeyError :
            args ={'parser_name':parser_name ,
            "":', '.join (self ._name_parser_map )}
            msg =_ ('unknown parser %(parser_name)r (choices: %(choices)s)')%args
            raise ArgumentError (self ,msg )
        if parser_name in self ._deprecated :
            parser ._warning (_ ("command '%(parser_name)s' is deprecated")%
            {'parser_name':parser_name })
        subnamespace ,arg_strings =subparser .parse_known_args (arg_strings ,None )
        for key ,value in vars (subnamespace ).items ():
            setattr (namespace ,key ,value )
        if arg_strings :
            if not hasattr (namespace ,_UNRECOGNIZED_ARGS_ATTR ):
                setattr (namespace ,_UNRECOGNIZED_ARGS_ATTR ,[])
            getattr (namespace ,_UNRECOGNIZED_ARGS_ATTR ).extend (arg_strings )
class _ExtendAction (_AppendAction ):
    def __call__ (self ,parser ,namespace ,values ,option_string =None ):
        items =getattr (namespace ,self .dest ,None )
        items =_copy_items (items )
        items .extend (values )
        setattr (namespace ,self .dest ,items )
class FileType (object ):
    def __init__ (self ,mode ='r',bufsize =-1 ,encoding =None ,errors =None ):
        self ._mode =mode
        self ._bufsize =bufsize
        self ._encoding =encoding
        self ._errors =errors
    def __call__ (self ,string ):
        if string =='-':
            if 'r'in self ._mode :
                return _sys .stdin .buffer if 'b'in self ._mode else _sys .stdin
            elif any (c in self ._mode for c in 'wax'):
                return _sys .stdout .buffer if 'b'in self ._mode else _sys .stdout
            else :
                msg =_ ('argument "-" with mode %r')%self ._mode
                raise ValueError (msg )
        try :
            return open (string ,self ._mode ,self ._bufsize ,self ._encoding ,
            self ._errors )
        except OSError as e :
            args ={'filename':string ,'error':e }
            message =_ ("can't open '%(filename)s': %(error)s")
            raise ArgumentTypeError (message %args )
    def __repr__ (self ):
        args =self ._mode ,self ._bufsize
        kwargs =[('encoding',self ._encoding ),('errors',self ._errors )]
        args_str =', '.join ([repr (arg )for arg in args if arg !=-1 ]+
        ['%s=%r'%(kw ,arg )for kw ,arg in kwargs
        if arg is not None ])
        return '%s(%s)'%(type (self ).__name__ ,args_str )
class Namespace (_AttributeHolder ):
    def __init__ (self ,**kwargs ):
        for name in kwargs :
            setattr (self ,name ,kwargs [name ])
    def __eq__ (self ,other ):
        if not isinstance (other ,Namespace ):
            return NotImplemented
        return vars (self )==vars (other )
    def __contains__ (self ,key ):
        return key in self .__dict__
class _ActionsContainer (object ):
    def __init__ (self ,
    description ,
    prefix_chars ,
    argument_default ,
    conflict_handler ):
        super (_ActionsContainer ,self ).__init__ ()
        self .description =description
        self .argument_default =argument_default
        self .prefix_chars =prefix_chars
        self .conflict_handler =conflict_handler
        self ._registries ={}
        self .register ('action',None ,_StoreAction )
        self .register ('action','store',_StoreAction )
        self .register ('action','store_const',_StoreConstAction )
        self .register ('action','store_true',_StoreTrueAction )
        self .register ('action','store_false',_StoreFalseAction )
        self .register ('action','append',_AppendAction )
        self .register ('action','append_const',_AppendConstAction )
        self .register ('action','count',_CountAction )
        self .register ('action','help',_HelpAction )
        self .register ('action','version',_VersionAction )
        self .register ('action','parsers',_SubParsersAction )
        self .register ('action','extend',_ExtendAction )
        self ._get_handler ()
        self ._actions =[]
        self ._option_string_actions ={}
        self ._action_groups =[]
        self ._mutually_exclusive_groups =[]
        self ._defaults ={}
        self ._negative_number_matcher =_re .compile (r'^-\d+$|^-\d*\.\d+$')
        self ._has_negative_number_optionals =[]
    def register (self ,registry_name ,value ,object ):
        registry =self ._registries .setdefault (registry_name ,{})
        registry [value ]=object
    def _registry_get (self ,registry_name ,value ,default =None ):
        return self ._registries [registry_name ].get (value ,default )
    def set_defaults (self ,**kwargs ):
        self ._defaults .update (kwargs )
        for action in self ._actions :
            if action .dest in kwargs :
                action .default =kwargs [action .dest ]
    def get_default (self ,dest ):
        for action in self ._actions :
            if action .dest ==dest and action .default is not None :
                return action .default
        return self ._defaults .get (dest ,None )
    def add_argument (self ,*args ,**kwargs ):
        chars =self .prefix_chars
        if not args or len (args )==1 and args [0 ][0 ]not in chars :
            if args and 'dest'in kwargs :
                raise ValueError ('dest supplied twice for positional argument')
            kwargs =self ._get_positional_kwargs (*args ,**kwargs )
        else :
            kwargs =self ._get_optional_kwargs (*args ,**kwargs )
        if 'default'not in kwargs :
            dest =kwargs ['dest']
            if dest in self ._defaults :
                kwargs ['default']=self ._defaults [dest ]
            elif self .argument_default is not None :
                kwargs ['default']=self .argument_default
        action_class =self ._pop_action_class (kwargs )
        if not callable (action_class ):
            raise ValueError ('unknown action "%s"'%(action_class ,))
        action =action_class (**kwargs )
        type_func =self ._registry_get ('type',action .type ,action .type )
        if not callable (type_func ):
            raise ValueError ('%r is not callable'%(type_func ,))
        if type_func is FileType :
            raise ValueError ('%r is a FileType class object, instance of it'
            ""%(type_func ,))
        if hasattr (self ,"_get_formatter"):
            try :
                self ._get_formatter ()._format_args (action ,None )
            except TypeError :
                raise ValueError ("length of metavar tuple does not match nargs")
        return self ._add_action (action )
    def add_argument_group (self ,*args ,**kwargs ):
        group =_ArgumentGroup (self ,*args ,**kwargs )
        self ._action_groups .append (group )
        return group
    def add_mutually_exclusive_group (self ,**kwargs ):
        group =_MutuallyExclusiveGroup (self ,**kwargs )
        self ._mutually_exclusive_groups .append (group )
        return group
    def _add_action (self ,action ):
        self ._check_conflict (action )
        self ._actions .append (action )
        action .container =self
        for option_string in action .option_strings :
            self ._option_string_actions [option_string ]=action
        for option_string in action .option_strings :
            if self ._negative_number_matcher .match (option_string ):
                if not self ._has_negative_number_optionals :
                    self ._has_negative_number_optionals .append (True )
        return action
    def _remove_action (self ,action ):
        self ._actions .remove (action )
    def _add_container_actions (self ,container ):
        title_group_map ={}
        for group in self ._action_groups :
            if group .title in title_group_map :
                msg =_ ('cannot merge actions - two groups are named %r')
                raise ValueError (msg %(group .title ))
            title_group_map [group .title ]=group
        group_map ={}
        for group in container ._action_groups :
            if group .title not in title_group_map :
                title_group_map [group .title ]=self .add_argument_group (
                title =group .title ,
                description =group .description ,
                conflict_handler =group .conflict_handler )
            for action in group ._group_actions :
                group_map [action ]=title_group_map [group .title ]
        for group in container ._mutually_exclusive_groups :
            if group ._container is container :
                cont =self
            else :
                cont =title_group_map [group ._container .title ]
            mutex_group =cont .add_mutually_exclusive_group (
            required =group .required )
            for action in group ._group_actions :
                group_map [action ]=mutex_group
        for action in container ._actions :
            group_map .get (action ,self )._add_action (action )
    def _get_positional_kwargs (self ,dest ,**kwargs ):
        if 'required'in kwargs :
            msg =_ ("'required' is an invalid argument for positionals")
            raise TypeError (msg )
        nargs =kwargs .get ('nargs')
        if nargs not in [OPTIONAL ,ZERO_OR_MORE ,REMAINDER ,SUPPRESS ,0 ]:
            kwargs ['required']=True
        return dict (kwargs ,dest =dest ,option_strings =[])
    def _get_optional_kwargs (self ,*args ,**kwargs ):
        option_strings =[]
        long_option_strings =[]
        for option_string in args :
            if not option_string [0 ]in self .prefix_chars :
                args ={'option':option_string ,
                "":self .prefix_chars }
                msg =_ ('invalid option string %(option)r: '
                "")
                raise ValueError (msg %args )
            option_strings .append (option_string )
            if len (option_string )>1 and option_string [1 ]in self .prefix_chars :
                long_option_strings .append (option_string )
        dest =kwargs .pop ('dest',None )
        if dest is None :
            if long_option_strings :
                dest_option_string =long_option_strings [0 ]
            else :
                dest_option_string =option_strings [0 ]
            dest =dest_option_string .lstrip (self .prefix_chars )
            if not dest :
                msg =_ ('dest= is required for options like %r')
                raise ValueError (msg %option_string )
            dest =dest .replace ('-','_')
        return dict (kwargs ,dest =dest ,option_strings =option_strings )
    def _pop_action_class (self ,kwargs ,default =None ):
        action =kwargs .pop ('action',default )
        return self ._registry_get ('action',action ,action )
    def _get_handler (self ):
        handler_func_name ='_handle_conflict_%s'%self .conflict_handler
        try :
            return getattr (self ,handler_func_name )
        except AttributeError :
            msg =_ ('invalid conflict_resolution value: %r')
            raise ValueError (msg %self .conflict_handler )
    def _check_conflict (self ,action ):
        confl_optionals =[]
        for option_string in action .option_strings :
            if option_string in self ._option_string_actions :
                confl_optional =self ._option_string_actions [option_string ]
                confl_optionals .append ((option_string ,confl_optional ))
        if confl_optionals :
            conflict_handler =self ._get_handler ()
            conflict_handler (action ,confl_optionals )
    def _handle_conflict_error (self ,action ,conflicting_actions ):
        message =ngettext ('conflicting option string: %s',
        "",
        len (conflicting_actions ))
        conflict_string =', '.join ([option_string
        for option_string ,action
        in conflicting_actions ])
        raise ArgumentError (action ,message %conflict_string )
    def _handle_conflict_resolve (self ,action ,conflicting_actions ):
        for option_string ,action in conflicting_actions :
            action .option_strings .remove (option_string )
            self ._option_string_actions .pop (option_string ,None )
            if not action .option_strings :
                action .container ._remove_action (action )
class _ArgumentGroup (_ActionsContainer ):
    def __init__ (self ,container ,title =None ,description =None ,**kwargs ):
        update =kwargs .setdefault
        update ('conflict_handler',container .conflict_handler )
        update ('prefix_chars',container .prefix_chars )
        update ('argument_default',container .argument_default )
        super_init =super (_ArgumentGroup ,self ).__init__
        super_init (description =description ,**kwargs )
        self .title =title
        self ._group_actions =[]
        self ._registries =container ._registries
        self ._actions =container ._actions
        self ._option_string_actions =container ._option_string_actions
        self ._defaults =container ._defaults
        self ._has_negative_number_optionals =container ._has_negative_number_optionals
        self ._mutually_exclusive_groups =container ._mutually_exclusive_groups
    def _add_action (self ,action ):
        action =super (_ArgumentGroup ,self )._add_action (action )
        self ._group_actions .append (action )
        return action
    def _remove_action (self ,action ):
        super (_ArgumentGroup ,self )._remove_action (action )
        self ._group_actions .remove (action )
    def add_argument_group (self ,*args ,**kwargs ):
        import warnings
        warnings .warn (
        "",
        category =DeprecationWarning ,
        stacklevel =2
        )
        return super ().add_argument_group (*args ,**kwargs )
class _MutuallyExclusiveGroup (_ArgumentGroup ):
    def __init__ (self ,container ,required =False ):
        super (_MutuallyExclusiveGroup ,self ).__init__ (container )
        self .required =required
        self ._container =container
    def _add_action (self ,action ):
        if action .required :
            msg =_ ('mutually exclusive arguments must be optional')
            raise ValueError (msg )
        action =self ._container ._add_action (action )
        self ._group_actions .append (action )
        return action
    def _remove_action (self ,action ):
        self ._container ._remove_action (action )
        self ._group_actions .remove (action )
    def add_mutually_exclusive_group (self ,*args ,**kwargs ):
        import warnings
        warnings .warn (
        "",
        category =DeprecationWarning ,
        stacklevel =2
        )
        return super ().add_mutually_exclusive_group (*args ,**kwargs )
class ArgumentParser (_AttributeHolder ,_ActionsContainer ):
    def __init__ (self ,
    prog =None ,
    usage =None ,
    description =None ,
    epilog =None ,
    parents =[],
    formatter_class =HelpFormatter ,
    prefix_chars ='-',
    fromfile_prefix_chars =None ,
    argument_default =None ,
    conflict_handler ='error',
    add_help =True ,
    allow_abbrev =True ,
    exit_on_error =True ):
        superinit =super (ArgumentParser ,self ).__init__
        superinit (description =description ,
        prefix_chars =prefix_chars ,
        argument_default =argument_default ,
        conflict_handler =conflict_handler )
        if prog is None :
            prog =_os .path .basename (_sys .argv [0 ])
        self .prog =prog
        self .usage =usage
        self .epilog =epilog
        self .formatter_class =formatter_class
        self .fromfile_prefix_chars =fromfile_prefix_chars
        self .add_help =add_help
        self .allow_abbrev =allow_abbrev
        self .exit_on_error =exit_on_error
        add_group =self .add_argument_group
        self ._positionals =add_group (_ ('positional arguments'))
        self ._optionals =add_group (_ ('options'))
        self ._subparsers =None
        def identity (string ):
            return string
        self .register ('type',None ,identity )
        default_prefix ='-'if '-'in prefix_chars else prefix_chars [0 ]
        if self .add_help :
            self .add_argument (
            default_prefix +'h',default_prefix *2 +'help',
            action ='help',default =SUPPRESS ,
            help =_ ('show this help message and exit'))
        for parent in parents :
            if not isinstance (parent ,ArgumentParser ):
                raise TypeError ('parents must be a list of ArgumentParser')
            self ._add_container_actions (parent )
            defaults =parent ._defaults
            self ._defaults .update (defaults )
    def _get_kwargs (self ):
        names =[
        "",
        "",
        "",
        "",
        "",
        "",
        ]
        return [(name ,getattr (self ,name ))for name in names ]
    def add_subparsers (self ,**kwargs ):
        if self ._subparsers is not None :
            raise ArgumentError (None ,_ ('cannot have multiple subparser arguments'))
        kwargs .setdefault ('parser_class',type (self ))
        if 'title'in kwargs or 'description'in kwargs :
            title =kwargs .pop ('title',_ ('subcommands'))
            description =kwargs .pop ('description',None )
            self ._subparsers =self .add_argument_group (title ,description )
        else :
            self ._subparsers =self ._positionals
        if kwargs .get ('prog')is None :
            formatter =self ._get_formatter ()
            positionals =self ._get_positional_actions ()
            groups =self ._mutually_exclusive_groups
            formatter .add_usage (self .usage ,positionals ,groups ,'')
            kwargs ['prog']=formatter .format_help ().strip ()
        parsers_class =self ._pop_action_class (kwargs ,'parsers')
        action =parsers_class (option_strings =[],**kwargs )
        self ._subparsers ._add_action (action )
        return action
    def _add_action (self ,action ):
        if action .option_strings :
            self ._optionals ._add_action (action )
        else :
            self ._positionals ._add_action (action )
        return action
    def _get_optional_actions (self ):
        return [action
        for action in self ._actions
        if action .option_strings ]
    def _get_positional_actions (self ):
        return [action
        for action in self ._actions
        if not action .option_strings ]
    def parse_args (self ,args =None ,namespace =None ):
        args ,argv =self .parse_known_args (args ,namespace )
        if argv :
            msg =_ ('unrecognized arguments: %s')%' '.join (argv )
            if self .exit_on_error :
                self .error (msg )
            else :
                raise ArgumentError (None ,msg )
        return args
    def parse_known_args (self ,args =None ,namespace =None ):
        return self ._parse_known_args2 (args ,namespace ,intermixed =False )
    def _parse_known_args2 (self ,args ,namespace ,intermixed ):
        if args is None :
            args =_sys .argv [1 :]
        else :
            args =list (args )
        if namespace is None :
            namespace =Namespace ()
        for action in self ._actions :
            if action .dest is not SUPPRESS :
                if not hasattr (namespace ,action .dest ):
                    if action .default is not SUPPRESS :
                        setattr (namespace ,action .dest ,action .default )
        for dest in self ._defaults :
            if not hasattr (namespace ,dest ):
                setattr (namespace ,dest ,self ._defaults [dest ])
        if self .exit_on_error :
            try :
                namespace ,args =self ._parse_known_args (args ,namespace ,intermixed )
            except ArgumentError as err :
                self .error (str (err ))
        else :
            namespace ,args =self ._parse_known_args (args ,namespace ,intermixed )
        if hasattr (namespace ,_UNRECOGNIZED_ARGS_ATTR ):
            args .extend (getattr (namespace ,_UNRECOGNIZED_ARGS_ATTR ))
            delattr (namespace ,_UNRECOGNIZED_ARGS_ATTR )
        return namespace ,args
    def _parse_known_args (self ,arg_strings ,namespace ,intermixed ):
        if self .fromfile_prefix_chars is not None :
            arg_strings =self ._read_args_from_files (arg_strings )
        action_conflicts ={}
        for mutex_group in self ._mutually_exclusive_groups :
            group_actions =mutex_group ._group_actions
            for i ,mutex_action in enumerate (mutex_group ._group_actions ):
                conflicts =action_conflicts .setdefault (mutex_action ,[])
                conflicts .extend (group_actions [:i ])
                conflicts .extend (group_actions [i +1 :])
        option_string_indices ={}
        arg_string_pattern_parts =[]
        arg_strings_iter =iter (arg_strings )
        for i ,arg_string in enumerate (arg_strings_iter ):
            if arg_string =='--':
                arg_string_pattern_parts .append ('-')
                for arg_string in arg_strings_iter :
                    arg_string_pattern_parts .append ('A')
            else :
                option_tuples =self ._parse_optional (arg_string )
                if option_tuples is None :
                    pattern ='A'
                else :
                    option_string_indices [i ]=option_tuples
                    pattern ='O'
                arg_string_pattern_parts .append (pattern )
        arg_strings_pattern =''.join (arg_string_pattern_parts )
        seen_actions =set ()
        seen_non_default_actions =set ()
        warned =set ()
        def take_action (action ,argument_strings ,option_string =None ):
            seen_actions .add (action )
            argument_values =self ._get_values (action ,argument_strings )
            if action .option_strings or argument_strings :
                seen_non_default_actions .add (action )
                for conflict_action in action_conflicts .get (action ,[]):
                    if conflict_action in seen_non_default_actions :
                        msg =_ ('not allowed with argument %s')
                        action_name =_get_action_name (conflict_action )
                        raise ArgumentError (action ,msg %action_name )
            if argument_values is not SUPPRESS :
                action (self ,namespace ,argument_values ,option_string )
        def consume_optional (start_index ):
            option_tuples =option_string_indices [start_index ]
            if len (option_tuples )>1 :
                options =', '.join ([option_string
                for action ,option_string ,sep ,explicit_arg in option_tuples ])
                args ={'option':arg_strings [start_index ],'matches':options }
                msg =_ ('ambiguous option: %(option)s could match %(matches)s')
                raise ArgumentError (None ,msg %args )
            action ,option_string ,sep ,explicit_arg =option_tuples [0 ]
            match_argument =self ._match_argument
            action_tuples =[]
            while True :
                if action is None :
                    extras .append (arg_strings [start_index ])
                    extras_pattern .append ('O')
                    return start_index +1
                if explicit_arg is not None :
                    arg_count =match_argument (action ,'A')
                    chars =self .prefix_chars
                    if (
                    arg_count ==0
                    and option_string [1 ]not in chars
                    and explicit_arg !=''
                    ):
                        if sep or explicit_arg [0 ]in chars :
                            msg =_ ('ignored explicit argument %r')
                            raise ArgumentError (action ,msg %explicit_arg )
                        action_tuples .append ((action ,[],option_string ))
                        char =option_string [0 ]
                        option_string =char +explicit_arg [0 ]
                        optionals_map =self ._option_string_actions
                        if option_string in optionals_map :
                            action =optionals_map [option_string ]
                            explicit_arg =explicit_arg [1 :]
                            if not explicit_arg :
                                sep =explicit_arg =None
                            elif explicit_arg [0 ]=='=':
                                sep ='='
                                explicit_arg =explicit_arg [1 :]
                            else :
                                sep =''
                        else :
                            extras .append (char +explicit_arg )
                            extras_pattern .append ('O')
                            stop =start_index +1
                            break
                    elif arg_count ==1 :
                        stop =start_index +1
                        args =[explicit_arg ]
                        action_tuples .append ((action ,args ,option_string ))
                        break
                    else :
                        msg =_ ('ignored explicit argument %r')
                        raise ArgumentError (action ,msg %explicit_arg )
                else :
                    start =start_index +1
                    selected_patterns =arg_strings_pattern [start :]
                    arg_count =match_argument (action ,selected_patterns )
                    stop =start +arg_count
                    args =arg_strings [start :stop ]
                    action_tuples .append ((action ,args ,option_string ))
                    break
            assert action_tuples
            for action ,args ,option_string in action_tuples :
                if action .deprecated and option_string not in warned :
                    self ._warning (_ ("option '%(option)s' is deprecated")%
                    {'option':option_string })
                    warned .add (option_string )
                take_action (action ,args ,option_string )
            return stop
        positionals =self ._get_positional_actions ()
        def consume_positionals (start_index ):
            match_partial =self ._match_arguments_partial
            selected_pattern =arg_strings_pattern [start_index :]
            arg_counts =match_partial (positionals ,selected_pattern )
            for action ,arg_count in zip (positionals ,arg_counts ):
                args =arg_strings [start_index :start_index +arg_count ]
                if action .nargs ==PARSER :
                    if arg_strings_pattern [start_index ]=='-':
                        assert args [0 ]=='--'
                        args .remove ('--')
                elif action .nargs !=REMAINDER :
                    if (arg_strings_pattern .find ('-',start_index ,
                    start_index +arg_count )>=0 ):
                        args .remove ('--')
                start_index +=arg_count
                if args and action .deprecated and action .dest not in warned :
                    self ._warning (_ ("argument '%(argument_name)s' is deprecated")%
                    {'argument_name':action .dest })
                    warned .add (action .dest )
                take_action (action ,args )
            positionals [:]=positionals [len (arg_counts ):]
            return start_index
        extras =[]
        extras_pattern =[]
        start_index =0
        if option_string_indices :
            max_option_string_index =max (option_string_indices )
        else :
            max_option_string_index =-1
        while start_index <=max_option_string_index :
            next_option_string_index =start_index
            while next_option_string_index <=max_option_string_index :
                if next_option_string_index in option_string_indices :
                    break
                next_option_string_index +=1
            if not intermixed and start_index !=next_option_string_index :
                positionals_end_index =consume_positionals (start_index )
                if positionals_end_index >start_index :
                    start_index =positionals_end_index
                    continue
                else :
                    start_index =positionals_end_index
            if start_index not in option_string_indices :
                strings =arg_strings [start_index :next_option_string_index ]
                extras .extend (strings )
                extras_pattern .extend (arg_strings_pattern [start_index :next_option_string_index ])
                start_index =next_option_string_index
            start_index =consume_optional (start_index )
        if not intermixed :
            stop_index =consume_positionals (start_index )
            extras .extend (arg_strings [stop_index :])
        else :
            extras .extend (arg_strings [start_index :])
            extras_pattern .extend (arg_strings_pattern [start_index :])
            extras_pattern =''.join (extras_pattern )
            assert len (extras_pattern )==len (extras )
            arg_strings =[s for s ,c in zip (extras ,extras_pattern )if c !='O']
            arg_strings_pattern =extras_pattern .replace ('O','')
            stop_index =consume_positionals (0 )
            for i ,c in enumerate (extras_pattern ):
                if not stop_index :
                    break
                if c !='O':
                    stop_index -=1
                    extras [i ]=None
            extras =[s for s in extras if s is not None ]
        required_actions =[]
        for action in self ._actions :
            if action not in seen_actions :
                if action .required :
                    required_actions .append (_get_action_name (action ))
                else :
                    if (action .default is not None and
                    isinstance (action .default ,str )and
                    hasattr (namespace ,action .dest )and
                    action .default is getattr (namespace ,action .dest )):
                        setattr (namespace ,action .dest ,
                        self ._get_value (action ,action .default ))
        if required_actions :
            raise ArgumentError (None ,_ ('the following arguments are required: %s')%
            "".join (required_actions ))
        for group in self ._mutually_exclusive_groups :
            if group .required :
                for action in group ._group_actions :
                    if action in seen_non_default_actions :
                        break
                else :
                    names =[_get_action_name (action )
                    for action in group ._group_actions
                    if action .help is not SUPPRESS ]
                    msg =_ ('one of the arguments %s is required')
                    raise ArgumentError (None ,msg %' '.join (names ))
        return namespace ,extras
    def _read_args_from_files (self ,arg_strings ):
        new_arg_strings =[]
        for arg_string in arg_strings :
            if not arg_string or arg_string [0 ]not in self .fromfile_prefix_chars :
                new_arg_strings .append (arg_string )
            else :
                try :
                    with open (arg_string [1 :],
                    encoding =_sys .getfilesystemencoding (),
                    errors =_sys .getfilesystemencodeerrors ())as args_file :
                        arg_strings =[]
                        for arg_line in args_file .read ().splitlines ():
                            for arg in self .convert_arg_line_to_args (arg_line ):
                                arg_strings .append (arg )
                        arg_strings =self ._read_args_from_files (arg_strings )
                        new_arg_strings .extend (arg_strings )
                except OSError as err :
                    raise ArgumentError (None ,str (err ))
        return new_arg_strings
    def convert_arg_line_to_args (self ,arg_line ):
        return [arg_line ]
    def _match_argument (self ,action ,arg_strings_pattern ):
        nargs_pattern =self ._get_nargs_pattern (action )
        match =_re .match (nargs_pattern ,arg_strings_pattern )
        if match is None :
            nargs_errors ={
            None :_ ('expected one argument'),
            OPTIONAL :_ ('expected at most one argument'),
            ONE_OR_MORE :_ ('expected at least one argument'),
            }
            msg =nargs_errors .get (action .nargs )
            if msg is None :
                msg =ngettext ('expected %s argument',
                "",
                action .nargs )%action .nargs
            raise ArgumentError (action ,msg )
        return len (match .group (1 ))
    def _match_arguments_partial (self ,actions ,arg_strings_pattern ):
        for i in range (len (actions ),0 ,-1 ):
            actions_slice =actions [:i ]
            pattern =''.join ([self ._get_nargs_pattern (action )
            for action in actions_slice ])
            match =_re .match (pattern ,arg_strings_pattern )
            if match is not None :
                result =[len (string )for string in match .groups ()]
                if (match .end ()<len (arg_strings_pattern )
                and arg_strings_pattern [match .end ()]=='O'):
                    while result and not result [-1 ]:
                        del result [-1 ]
                return result
        return []
    def _parse_optional (self ,arg_string ):
        if not arg_string :
            return None
        if not arg_string [0 ]in self .prefix_chars :
            return None
        if arg_string in self ._option_string_actions :
            action =self ._option_string_actions [arg_string ]
            return [(action ,arg_string ,None ,None )]
        if len (arg_string )==1 :
            return None
        option_string ,sep ,explicit_arg =arg_string .partition ('=')
        if sep and option_string in self ._option_string_actions :
            action =self ._option_string_actions [option_string ]
            return [(action ,option_string ,sep ,explicit_arg )]
        option_tuples =self ._get_option_tuples (arg_string )
        if option_tuples :
            return option_tuples
        if self ._negative_number_matcher .match (arg_string ):
            if not self ._has_negative_number_optionals :
                return None
        if ' 'in arg_string :
            return None
        return [(None ,arg_string ,None ,None )]
    def _get_option_tuples (self ,option_string ):
        result =[]
        chars =self .prefix_chars
        if option_string [0 ]in chars and option_string [1 ]in chars :
            if self .allow_abbrev :
                option_prefix ,sep ,explicit_arg =option_string .partition ('=')
                if not sep :
                    sep =explicit_arg =None
                for option_string in self ._option_string_actions :
                    if option_string .startswith (option_prefix ):
                        action =self ._option_string_actions [option_string ]
                        tup =action ,option_string ,sep ,explicit_arg
                        result .append (tup )
        elif option_string [0 ]in chars and option_string [1 ]not in chars :
            option_prefix ,sep ,explicit_arg =option_string .partition ('=')
            if not sep :
                sep =explicit_arg =None
            short_option_prefix =option_string [:2 ]
            short_explicit_arg =option_string [2 :]
            for option_string in self ._option_string_actions :
                if option_string ==short_option_prefix :
                    action =self ._option_string_actions [option_string ]
                    tup =action ,option_string ,'',short_explicit_arg
                    result .append (tup )
                elif self .allow_abbrev and option_string .startswith (option_prefix ):
                    action =self ._option_string_actions [option_string ]
                    tup =action ,option_string ,sep ,explicit_arg
                    result .append (tup )
        else :
            raise ArgumentError (None ,_ ('unexpected option string: %s')%option_string )
        return result
    def _get_nargs_pattern (self ,action ):
        nargs =action .nargs
        option =action .option_strings
        if nargs is None :
            nargs_pattern ='([A])'if option else '(-*A-*)'
        elif nargs ==OPTIONAL :
            nargs_pattern ='(A?)'if option else '(-*A?-*)'
        elif nargs ==ZERO_OR_MORE :
            nargs_pattern ='(A*)'if option else '(-*[A-]*)'
        elif nargs ==ONE_OR_MORE :
            nargs_pattern ='(A+)'if option else '(-*A[A-]*)'
        elif nargs ==REMAINDER :
            nargs_pattern ='([AO]*)'if option else '(.*)'
        elif nargs ==PARSER :
            nargs_pattern ='(A[AO]*)'if option else '(-*A[-AO]*)'
        elif nargs ==SUPPRESS :
            nargs_pattern ='()'if option else '(-*)'
        else :
            nargs_pattern ='([AO]{%d})'%nargs if option else '((?:-*A){%d}-*)'%nargs
        return nargs_pattern
    def parse_intermixed_args (self ,args =None ,namespace =None ):
        args ,argv =self .parse_known_intermixed_args (args ,namespace )
        if argv :
            msg =_ ('unrecognized arguments: %s')%' '.join (argv )
            if self .exit_on_error :
                self .error (msg )
            else :
                raise ArgumentError (None ,msg )
        return args
    def parse_known_intermixed_args (self ,args =None ,namespace =None ):
        positionals =self ._get_positional_actions ()
        a =[action for action in positionals
        if action .nargs in [PARSER ,REMAINDER ]]
        if a :
            raise TypeError ('parse_intermixed_args: positional arg'
            ""%a [0 ].nargs )
        return self ._parse_known_args2 (args ,namespace ,intermixed =True )
    def _get_values (self ,action ,arg_strings ):
        if not arg_strings and action .nargs ==OPTIONAL :
            if action .option_strings :
                value =action .const
            else :
                value =action .default
            if isinstance (value ,str )and value is not SUPPRESS :
                value =self ._get_value (action ,value )
                self ._check_value (action ,value )
        elif (not arg_strings and action .nargs ==ZERO_OR_MORE and
        not action .option_strings ):
            if action .default is not None :
                value =action .default
                self ._check_value (action ,value )
            else :
                value =arg_strings
        elif len (arg_strings )==1 and action .nargs in [None ,OPTIONAL ]:
            arg_string ,=arg_strings
            value =self ._get_value (action ,arg_string )
            self ._check_value (action ,value )
        elif action .nargs ==REMAINDER :
            value =[self ._get_value (action ,v )for v in arg_strings ]
        elif action .nargs ==PARSER :
            value =[self ._get_value (action ,v )for v in arg_strings ]
            self ._check_value (action ,value [0 ])
        elif action .nargs ==SUPPRESS :
            value =SUPPRESS
        else :
            value =[self ._get_value (action ,v )for v in arg_strings ]
            for v in value :
                self ._check_value (action ,v )
        return value
    def _get_value (self ,action ,arg_string ):
        type_func =self ._registry_get ('type',action .type ,action .type )
        if not callable (type_func ):
            msg =_ ('%r is not callable')
            raise ArgumentError (action ,msg %type_func )
        try :
            result =type_func (arg_string )
        except ArgumentTypeError as err :
            msg =str (err )
            raise ArgumentError (action ,msg )
        except (TypeError ,ValueError ):
            name =getattr (action .type ,'__name__',repr (action .type ))
            args ={'type':name ,'value':arg_string }
            msg =_ ('invalid %(type)s value: %(value)r')
            raise ArgumentError (action ,msg %args )
        return result
    def _check_value (self ,action ,value ):
        choices =action .choices
        if choices is not None :
            if isinstance (choices ,str ):
                choices =iter (choices )
            if value not in choices :
                args ={'value':str (value ),
                "":', '.join (repr (str (choice ))for choice in action .choices )}
                msg =_ ('invalid choice: %(value)r (choose from %(choices)s)')
                raise ArgumentError (action ,msg %args )
    def format_usage (self ):
        formatter =self ._get_formatter ()
        formatter .add_usage (self .usage ,self ._actions ,
        self ._mutually_exclusive_groups )
        return formatter .format_help ()
    def format_help (self ):
        formatter =self ._get_formatter ()
        formatter .add_usage (self .usage ,self ._actions ,
        self ._mutually_exclusive_groups )
        formatter .add_text (self .description )
        for action_group in self ._action_groups :
            formatter .start_section (action_group .title )
            formatter .add_text (action_group .description )
            formatter .add_arguments (action_group ._group_actions )
            formatter .end_section ()
        formatter .add_text (self .epilog )
        return formatter .format_help ()
    def _get_formatter (self ):
        return self .formatter_class (prog =self .prog )
    def print_usage (self ,file =None ):
        if file is None :
            file =_sys .stdout
        self ._print_message (self .format_usage (),file )
    def print_help (self ,file =None ):
        if file is None :
            file =_sys .stdout
        self ._print_message (self .format_help (),file )
    def _print_message (self ,message ,file =None ):
        if message :
            file =file or _sys .stderr
            try :
                file .write (message )
            except (AttributeError ,OSError ):
                pass
    def exit (self ,status =0 ,message =None ):
        if message :
            self ._print_message (message ,_sys .stderr )
        _sys .exit (status )
    def error (self ,message ):
        self .print_usage (_sys .stderr )
        args ={'prog':self .prog ,'message':message }
        self .exit (2 ,_ ('%(prog)s: error: %(message)s\n')%args )
    def _warning (self ,message ):
        args ={'prog':self .prog ,'message':message }
        self ._print_message (_ ('%(prog)s: warning: %(message)s\n')%args ,_sys .stderr )
import sys
import datetime
from enum import IntEnum ,global_enum
import locale as _locale
from itertools import repeat
__all__ =["IllegalMonthError","IllegalWeekdayError","setfirstweekday",
"","isleap","leapdays","weekday","monthrange",
"","prmonth","month","prcal","calendar",
"","month_name","month_abbr","day_name","day_abbr",
"","TextCalendar","HTMLCalendar","LocaleTextCalendar",
"","weekheader",
"","Month","JANUARY","FEBRUARY","MARCH",
"","MAY","JUNE","JULY",
"","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER",
"","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY",
"","SUNDAY"]
error =ValueError
class IllegalMonthError (ValueError ,IndexError ):
    def __init__ (self ,month ):
        self .month =month
    def __str__ (self ):
        return "bad month number %r; must be 1-12"%self .month
class IllegalWeekdayError (ValueError ):
    def __init__ (self ,weekday ):
        self .weekday =weekday
    def __str__ (self ):
        return "bad weekday number %r; must be 0 (Monday) to 6 (Sunday)"%self .weekday
def __getattr__ (name ):
    if name in ('January','February'):
        import warnings
        warnings .warn (f"The '{name }' attribute is deprecated, use '{name .upper ()}' instead",
        DeprecationWarning ,stacklevel =2 )
        if name =='January':
            return 1
        else :
            return 2
    raise AttributeError (f"module '{__name__ }' has no attribute '{name }'")
@global_enum
class Month (IntEnum ):
    JANUARY =1
    FEBRUARY =2
    MARCH =3
    APRIL =4
    MAY =5
    JUNE =6
    JULY =7
    AUGUST =8
    SEPTEMBER =9
    OCTOBER =10
    NOVEMBER =11
    DECEMBER =12
@global_enum
class Day (IntEnum ):
    MONDAY =0
    TUESDAY =1
    WEDNESDAY =2
    THURSDAY =3
    FRIDAY =4
    SATURDAY =5
    SUNDAY =6
mdays =[0 ,31 ,28 ,31 ,30 ,31 ,30 ,31 ,31 ,30 ,31 ,30 ,31 ]
class _localized_month :
    _months =[datetime .date (2001 ,i +1 ,1 ).strftime for i in range (12 )]
    _months .insert (0 ,lambda x :"")
    def __init__ (self ,format ):
        self .format =format
    def __getitem__ (self ,i ):
        funcs =self ._months [i ]
        if isinstance (i ,slice ):
            return [f (self .format )for f in funcs ]
        else :
            return funcs (self .format )
    def __len__ (self ):
        return 13
class _localized_day :
    _days =[datetime .date (2001 ,1 ,i +1 ).strftime for i in range (7 )]
    def __init__ (self ,format ):
        self .format =format
    def __getitem__ (self ,i ):
        funcs =self ._days [i ]
        if isinstance (i ,slice ):
            return [f (self .format )for f in funcs ]
        else :
            return funcs (self .format )
    def __len__ (self ):
        return 7
day_name =_localized_day ('%A')
day_abbr =_localized_day ('%a')
month_name =_localized_month ('%B')
month_abbr =_localized_month ('%b')
def isleap (year ):
    return year %4 ==0 and (year %100 !=0 or year %400 ==0 )
def leapdays (y1 ,y2 ):
    y1 -=1
    y2 -=1
    return (y2 //4 -y1 //4 )-(y2 //100 -y1 //100 )+(y2 //400 -y1 //400 )
def weekday (year ,month ,day ):
    if not datetime .MINYEAR <=year <=datetime .MAXYEAR :
        year =2000 +year %400
    return Day (datetime .date (year ,month ,day ).weekday ())
def _validate_month (month ):
    if not 1 <=month <=12 :
        raise IllegalMonthError (month )
def monthrange (year ,month ):
    _validate_month (month )
    day1 =weekday (year ,month ,1 )
    ndays =mdays [month ]+(month ==FEBRUARY and isleap (year ))
    return day1 ,ndays
def _monthlen (year ,month ):
    return mdays [month ]+(month ==FEBRUARY and isleap (year ))
def _prevmonth (year ,month ):
    if month ==1 :
        return year -1 ,12
    else :
        return year ,month -1
def _nextmonth (year ,month ):
    if month ==12 :
        return year +1 ,1
    else :
        return year ,month +1
class Calendar (object ):
    def __init__ (self ,firstweekday =0 ):
        self .firstweekday =firstweekday
    def getfirstweekday (self ):
        return self ._firstweekday %7
    def setfirstweekday (self ,firstweekday ):
        self ._firstweekday =firstweekday
    firstweekday =property (getfirstweekday ,setfirstweekday )
    def iterweekdays (self ):
        for i in range (self .firstweekday ,self .firstweekday +7 ):
            yield i %7
    def itermonthdates (self ,year ,month ):
        for y ,m ,d in self .itermonthdays3 (year ,month ):
            yield datetime .date (y ,m ,d )
    def itermonthdays (self ,year ,month ):
        day1 ,ndays =monthrange (year ,month )
        days_before =(day1 -self .firstweekday )%7
        yield from repeat (0 ,days_before )
        yield from range (1 ,ndays +1 )
        days_after =(self .firstweekday -day1 -ndays )%7
        yield from repeat (0 ,days_after )
    def itermonthdays2 (self ,year ,month ):
        for i ,d in enumerate (self .itermonthdays (year ,month ),self .firstweekday ):
            yield d ,i %7
    def itermonthdays3 (self ,year ,month ):
        day1 ,ndays =monthrange (year ,month )
        days_before =(day1 -self .firstweekday )%7
        days_after =(self .firstweekday -day1 -ndays )%7
        y ,m =_prevmonth (year ,month )
        end =_monthlen (y ,m )+1
        for d in range (end -days_before ,end ):
            yield y ,m ,d
        for d in range (1 ,ndays +1 ):
            yield year ,month ,d
        y ,m =_nextmonth (year ,month )
        for d in range (1 ,days_after +1 ):
            yield y ,m ,d
    def itermonthdays4 (self ,year ,month ):
        for i ,(y ,m ,d )in enumerate (self .itermonthdays3 (year ,month )):
            yield y ,m ,d ,(self .firstweekday +i )%7
    def monthdatescalendar (self ,year ,month ):
        dates =list (self .itermonthdates (year ,month ))
        return [dates [i :i +7 ]for i in range (0 ,len (dates ),7 )]
    def monthdays2calendar (self ,year ,month ):
        days =list (self .itermonthdays2 (year ,month ))
        return [days [i :i +7 ]for i in range (0 ,len (days ),7 )]
    def monthdayscalendar (self ,year ,month ):
        days =list (self .itermonthdays (year ,month ))
        return [days [i :i +7 ]for i in range (0 ,len (days ),7 )]
    def yeardatescalendar (self ,year ,width =3 ):
        months =[self .monthdatescalendar (year ,m )for m in Month ]
        return [months [i :i +width ]for i in range (0 ,len (months ),width )]
    def yeardays2calendar (self ,year ,width =3 ):
        months =[self .monthdays2calendar (year ,m )for m in Month ]
        return [months [i :i +width ]for i in range (0 ,len (months ),width )]
    def yeardayscalendar (self ,year ,width =3 ):
        months =[self .monthdayscalendar (year ,m )for m in Month ]
        return [months [i :i +width ]for i in range (0 ,len (months ),width )]
class TextCalendar (Calendar ):
    def prweek (self ,theweek ,width ):
        print (self .formatweek (theweek ,width ),end ='')
    def formatday (self ,day ,weekday ,width ):
        if day ==0 :
            s =''
        else :
            s ='%2i'%day
        return s .center (width )
    def formatweek (self ,theweek ,width ):
        return ' '.join (self .formatday (d ,wd ,width )for (d ,wd )in theweek )
    def formatweekday (self ,day ,width ):
        if width >=9 :
            names =day_name
        else :
            names =day_abbr
        return names [day ][:width ].center (width )
    def formatweekheader (self ,width ):
        return ' '.join (self .formatweekday (i ,width )for i in self .iterweekdays ())
    def formatmonthname (self ,theyear ,themonth ,width ,withyear =True ):
        _validate_month (themonth )
        s =month_name [themonth ]
        if withyear :
            s ="%s %r"%(s ,theyear )
        return s .center (width )
    def prmonth (self ,theyear ,themonth ,w =0 ,l =0 ):
        print (self .formatmonth (theyear ,themonth ,w ,l ),end ='')
    def formatmonth (self ,theyear ,themonth ,w =0 ,l =0 ):
        w =max (2 ,w )
        l =max (1 ,l )
        s =self .formatmonthname (theyear ,themonth ,7 *(w +1 )-1 )
        s =s .rstrip ()
        s +='\n'*l
        s +=self .formatweekheader (w ).rstrip ()
        s +='\n'*l
        for week in self .monthdays2calendar (theyear ,themonth ):
            s +=self .formatweek (week ,w ).rstrip ()
            s +='\n'*l
        return s
    def formatyear (self ,theyear ,w =2 ,l =1 ,c =6 ,m =3 ):
        w =max (2 ,w )
        l =max (1 ,l )
        c =max (2 ,c )
        colwidth =(w +1 )*7 -1
        v =[]
        a =v .append
        a (repr (theyear ).center (colwidth *m +c *(m -1 )).rstrip ())
        a ('\n'*l )
        header =self .formatweekheader (w )
        for (i ,row )in enumerate (self .yeardays2calendar (theyear ,m )):
            months =range (m *i +1 ,min (m *(i +1 )+1 ,13 ))
            a ('\n'*l )
            names =(self .formatmonthname (theyear ,k ,colwidth ,False )
            for k in months )
            a (formatstring (names ,colwidth ,c ).rstrip ())
            a ('\n'*l )
            headers =(header for k in months )
            a (formatstring (headers ,colwidth ,c ).rstrip ())
            a ('\n'*l )
            height =max (len (cal )for cal in row )
            for j in range (height ):
                weeks =[]
                for cal in row :
                    if j >=len (cal ):
                        weeks .append ('')
                    else :
                        weeks .append (self .formatweek (cal [j ],w ))
                a (formatstring (weeks ,colwidth ,c ).rstrip ())
                a ('\n'*l )
        return ''.join (v )
    def pryear (self ,theyear ,w =0 ,l =0 ,c =6 ,m =3 ):
        print (self .formatyear (theyear ,w ,l ,c ,m ),end ='')
class HTMLCalendar (Calendar ):
    cssclasses =["mon","tue","wed","thu","fri","sat","sun"]
    cssclasses_weekday_head =cssclasses
    cssclass_noday ="noday"
    cssclass_month_head ="month"
    cssclass_month ="month"
    cssclass_year_head ="year"
    cssclass_year ="year"
    def formatday (self ,day ,weekday ):
        if day ==0 :
            return '<td class="%s">&nbsp;</td>'%self .cssclass_noday
        else :
            return '<td class="%s">%d</td>'%(self .cssclasses [weekday ],day )
    def formatweek (self ,theweek ):
        s =''.join (self .formatday (d ,wd )for (d ,wd )in theweek )
        return '<tr>%s</tr>'%s
    def formatweekday (self ,day ):
        return '<th class="%s">%s</th>'%(
        self .cssclasses_weekday_head [day ],day_abbr [day ])
    def formatweekheader (self ):
        s =''.join (self .formatweekday (i )for i in self .iterweekdays ())
        return '<tr>%s</tr>'%s
    def formatmonthname (self ,theyear ,themonth ,withyear =True ):
        _validate_month (themonth )
        if withyear :
            s ='%s %s'%(month_name [themonth ],theyear )
        else :
            s ='%s'%month_name [themonth ]
        return '<tr><th colspan="7" class="%s">%s</th></tr>'%(
        self .cssclass_month_head ,s )
    def formatmonth (self ,theyear ,themonth ,withyear =True ):
        v =[]
        a =v .append
        a ('<table border="0" cellpadding="0" cellspacing="0" class="%s">'%(
        self .cssclass_month ))
        a ('\n')
        a (self .formatmonthname (theyear ,themonth ,withyear =withyear ))
        a ('\n')
        a (self .formatweekheader ())
        a ('\n')
        for week in self .monthdays2calendar (theyear ,themonth ):
            a (self .formatweek (week ))
            a ('\n')
        a ('</table>')
        a ('\n')
        return ''.join (v )
    def formatyear (self ,theyear ,width =3 ):
        v =[]
        a =v .append
        width =max (width ,1 )
        a ('<table border="0" cellpadding="0" cellspacing="0" class="%s">'%
        self .cssclass_year )
        a ('\n')
        a ('<tr><th colspan="%d" class="%s">%s</th></tr>'%(
        width ,self .cssclass_year_head ,theyear ))
        for i in range (JANUARY ,JANUARY +12 ,width ):
            months =range (i ,min (i +width ,13 ))
            a ('<tr>')
            for m in months :
                a ('<td>')
                a (self .formatmonth (theyear ,m ,withyear =False ))
                a ('</td>')
            a ('</tr>')
        a ('</table>')
        return ''.join (v )
    def formatyearpage (self ,theyear ,width =3 ,css ='calendar.css',encoding =None ):
        if encoding is None :
            encoding =sys .getdefaultencoding ()
        v =[]
        a =v .append
        a ('<?xml version="1.0" encoding="%s"?>\n'%encoding )
        a ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n')
        a ('<html>\n')
        a ('<head>\n')
        a ('<meta http-equiv="Content-Type" content="text/html; charset=%s" />\n'%encoding )
        if css is not None :
            a ('<link rel="stylesheet" type="text/css" href="%s" />\n'%css )
        a ('<title>Calendar for %d</title>\n'%theyear )
        a ('</head>\n')
        a ('<body>\n')
        a (self .formatyear (theyear ,width ))
        a ('</body>\n')
        a ('</html>\n')
        return ''.join (v ).encode (encoding ,"xmlcharrefreplace")
class different_locale :
    def __init__ (self ,locale ):
        self .locale =locale
        self .oldlocale =None
    def __enter__ (self ):
        self .oldlocale =_locale .setlocale (_locale .LC_TIME ,None )
        _locale .setlocale (_locale .LC_TIME ,self .locale )
    def __exit__ (self ,*args ):
        _locale .setlocale (_locale .LC_TIME ,self .oldlocale )
def _get_default_locale ():
    locale =_locale .setlocale (_locale .LC_TIME ,None )
    if locale =="C":
        with different_locale (""):
            locale =_locale .setlocale (_locale .LC_TIME ,None )
    return locale
class LocaleTextCalendar (TextCalendar ):
    def __init__ (self ,firstweekday =0 ,locale =None ):
        TextCalendar .__init__ (self ,firstweekday )
        if locale is None :
            locale =_get_default_locale ()
        self .locale =locale
    def formatweekday (self ,day ,width ):
        with different_locale (self .locale ):
            return super ().formatweekday (day ,width )
    def formatmonthname (self ,theyear ,themonth ,width ,withyear =True ):
        with different_locale (self .locale ):
            return super ().formatmonthname (theyear ,themonth ,width ,withyear )
class LocaleHTMLCalendar (HTMLCalendar ):
    def __init__ (self ,firstweekday =0 ,locale =None ):
        HTMLCalendar .__init__ (self ,firstweekday )
        if locale is None :
            locale =_get_default_locale ()
        self .locale =locale
    def formatweekday (self ,day ):
        with different_locale (self .locale ):
            return super ().formatweekday (day )
    def formatmonthname (self ,theyear ,themonth ,withyear =True ):
        with different_locale (self .locale ):
            return super ().formatmonthname (theyear ,themonth ,withyear )
c =TextCalendar ()
firstweekday =c .getfirstweekday
def setfirstweekday (firstweekday ):
    if not MONDAY <=firstweekday <=SUNDAY :
        raise IllegalWeekdayError (firstweekday )
    c .firstweekday =firstweekday
monthcalendar =c .monthdayscalendar
prweek =c .prweek
week =c .formatweek
weekheader =c .formatweekheader
prmonth =c .prmonth
month =c .formatmonth
calendar =c .formatyear
prcal =c .pryear
_colwidth =7 *3 -1
_spacing =6
def format (cols ,colwidth =_colwidth ,spacing =_spacing ):
    print (formatstring (cols ,colwidth ,spacing ))
def formatstring (cols ,colwidth =_colwidth ,spacing =_spacing ):
    spacing *=' '
    return spacing .join (c .center (colwidth )for c in cols )
EPOCH =1970
_EPOCH_ORD =datetime .date (EPOCH ,1 ,1 ).toordinal ()
def timegm (tuple ):
    year ,month ,day ,hour ,minute ,second =tuple [:6 ]
    days =datetime .date (year ,month ,1 ).toordinal ()-_EPOCH_ORD +day -1
    hours =days *24 +hour
    minutes =hours *60 +minute
    seconds =minutes *60 +second
    return seconds
def main (args =None ):
    import argparse
    parser =argparse .ArgumentParser ()
    textgroup =parser .add_argument_group ('text only arguments')
    htmlgroup =parser .add_argument_group ('html only arguments')
    textgroup .add_argument (
    "","--width",
    type =int ,default =2 ,
    help ="width of date column (default 2)"
    )
    textgroup .add_argument (
    "","--lines",
    type =int ,default =1 ,
    help ="number of lines for each week (default 1)"
    )
    textgroup .add_argument (
    "","--spacing",
    type =int ,default =6 ,
    help ="spacing between months (default 6)"
    )
    textgroup .add_argument (
    "","--months",
    type =int ,default =3 ,
    help ="months per row (default 3)"
    )
    htmlgroup .add_argument (
    "","--css",
    default ="calendar.css",
    help ="CSS to use for page"
    )
    parser .add_argument (
    "","--locale",
    default =None ,
    help ="locale to use for month and weekday names"
    )
    parser .add_argument (
    "","--encoding",
    default =None ,
    help ="encoding to use for output"
    )
    parser .add_argument (
    "","--type",
    default ="text",
    choices =("text","html"),
    help ="output type (text or html)"
    )
    parser .add_argument (
    "","--first-weekday",
    type =int ,default =0 ,
    help ="weekday (0 is Monday, 6 is Sunday) to start each week (default 0)"
    )
    parser .add_argument (
    "",
    nargs ='?',type =int ,
    help ="year number"
    )
    parser .add_argument (
    "",
    nargs ='?',type =int ,
    help ="month number (1-12, text only)"
    )
    options =parser .parse_args (args )
    if options .locale and not options .encoding :
        parser .error ("if --locale is specified --encoding is required")
        sys .exit (1 )
    locale =options .locale ,options .encoding
    if options .type =="html":
        if options .month :
            parser .error ("incorrect number of arguments")
            sys .exit (1 )
        if options .locale :
            cal =LocaleHTMLCalendar (locale =locale )
        else :
            cal =HTMLCalendar ()
        cal .setfirstweekday (options .first_weekday )
        encoding =options .encoding
        if encoding is None :
            encoding =sys .getdefaultencoding ()
        optdict =dict (encoding =encoding ,css =options .css )
        write =sys .stdout .buffer .write
        if options .year is None :
            write (cal .formatyearpage (datetime .date .today ().year ,**optdict ))
        else :
            write (cal .formatyearpage (options .year ,**optdict ))
    else :
        if options .locale :
            cal =LocaleTextCalendar (locale =locale )
        else :
            cal =TextCalendar ()
        cal .setfirstweekday (options .first_weekday )
        optdict =dict (w =options .width ,l =options .lines )
        if options .month is None :
            optdict ["c"]=options .spacing
            optdict ["m"]=options .months
        if options .month is not None :
            _validate_month (options .month )
        if options .year is None :
            result =cal .formatyear (datetime .date .today ().year ,**optdict )
        elif options .month is None :
            result =cal .formatyear (options .year ,**optdict )
        else :
            result =cal .formatmonth (options .year ,options .month ,**optdict )
        write =sys .stdout .write
        if options .encoding :
            result =result .encode (options .encoding )
            write =sys .stdout .buffer .write
        write (result )
if __name__ =="__main__":
    main ()
import os
import re
import sys
from collections import deque
from io import StringIO
__all__ =["shlex","split","quote","join"]
class shlex :
    def __init__ (self ,instream =None ,infile =None ,posix =False ,
    punctuation_chars =False ):
        if isinstance (instream ,str ):
            instream =StringIO (instream )
        if instream is not None :
            self .instream =instream
            self .infile =infile
        else :
            self .instream =sys .stdin
            self .infile =None
        self .posix =posix
        if posix :
            self .eof =None
        else :
            self .eof =''
        self .commenters ='#'
        self .wordchars =('abcdfeghijklmnopqrstuvwxyz'
        "")
        if self .posix :
            self .wordchars +=('ßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
            "")
        self .whitespace =' \t\r\n'
        self .whitespace_split =False
        self .quotes ='\'"'
        self .escape ='\\'
        self .escapedquotes ='"'
        self .state =' '
        self .pushback =deque ()
        self .lineno =1
        self .debug =0
        self .token =''
        self .filestack =deque ()
        self .source =None
        if not punctuation_chars :
            punctuation_chars =''
        elif punctuation_chars is True :
            punctuation_chars ='();<>|&'
        self ._punctuation_chars =punctuation_chars
        if punctuation_chars :
            self ._pushback_chars =deque ()
            self .wordchars +='~-./*?='
            t =self .wordchars .maketrans (dict .fromkeys (punctuation_chars ))
            self .wordchars =self .wordchars .translate (t )
    @property
    def punctuation_chars (self ):
        return self ._punctuation_chars
    def push_token (self ,tok ):
        if self .debug >=1 :
            print ("shlex: pushing token "+repr (tok ))
        self .pushback .appendleft (tok )
    def push_source (self ,newstream ,newfile =None ):
        if isinstance (newstream ,str ):
            newstream =StringIO (newstream )
        self .filestack .appendleft ((self .infile ,self .instream ,self .lineno ))
        self .infile =newfile
        self .instream =newstream
        self .lineno =1
        if self .debug :
            if newfile is not None :
                print ('shlex: pushing to file %s'%(self .infile ,))
            else :
                print ('shlex: pushing to stream %s'%(self .instream ,))
    def pop_source (self ):
        self .instream .close ()
        (self .infile ,self .instream ,self .lineno )=self .filestack .popleft ()
        if self .debug :
            print ('shlex: popping to %s, line %d'%(self .instream ,self .lineno ))
        self .state =' '
    def get_token (self ):
        if self .pushback :
            tok =self .pushback .popleft ()
            if self .debug >=1 :
                print ("shlex: popping token "+repr (tok ))
            return tok
        raw =self .read_token ()
        if self .source is not None :
            while raw ==self .source :
                spec =self .sourcehook (self .read_token ())
                if spec :
                    (newfile ,newstream )=spec
                    self .push_source (newstream ,newfile )
                raw =self .get_token ()
        while raw ==self .eof :
            if not self .filestack :
                return self .eof
            else :
                self .pop_source ()
                raw =self .get_token ()
        if self .debug >=1 :
            if raw !=self .eof :
                print ("shlex: token="+repr (raw ))
            else :
                print ("shlex: token=EOF")
        return raw
    def read_token (self ):
        quoted =False
        escapedstate =' '
        while True :
            if self .punctuation_chars and self ._pushback_chars :
                nextchar =self ._pushback_chars .pop ()
            else :
                nextchar =self .instream .read (1 )
            if nextchar =='\n':
                self .lineno +=1
            if self .debug >=3 :
                print ("shlex: in state %r I see character: %r"%(self .state ,
                nextchar ))
            if self .state is None :
                self .token =''
                break
            elif self .state ==' ':
                if not nextchar :
                    self .state =None
                    break
                elif nextchar in self .whitespace :
                    if self .debug >=2 :
                        print ("shlex: I see whitespace in whitespace state")
                    if self .token or (self .posix and quoted ):
                        break
                    else :
                        continue
                elif nextchar in self .commenters :
                    self .instream .readline ()
                    self .lineno +=1
                elif self .posix and nextchar in self .escape :
                    escapedstate ='a'
                    self .state =nextchar
                elif nextchar in self .wordchars :
                    self .token =nextchar
                    self .state ='a'
                elif nextchar in self .punctuation_chars :
                    self .token =nextchar
                    self .state ='c'
                elif nextchar in self .quotes :
                    if not self .posix :
                        self .token =nextchar
                    self .state =nextchar
                elif self .whitespace_split :
                    self .token =nextchar
                    self .state ='a'
                else :
                    self .token =nextchar
                    if self .token or (self .posix and quoted ):
                        break
                    else :
                        continue
            elif self .state in self .quotes :
                quoted =True
                if not nextchar :
                    if self .debug >=2 :
                        print ("shlex: I see EOF in quotes state")
                    raise ValueError ("No closing quotation")
                if nextchar ==self .state :
                    if not self .posix :
                        self .token +=nextchar
                        self .state =' '
                        break
                    else :
                        self .state ='a'
                elif (self .posix and nextchar in self .escape and self .state
                in self .escapedquotes ):
                    escapedstate =self .state
                    self .state =nextchar
                else :
                    self .token +=nextchar
            elif self .state in self .escape :
                if not nextchar :
                    if self .debug >=2 :
                        print ("shlex: I see EOF in escape state")
                    raise ValueError ("No escaped character")
                if (escapedstate in self .quotes and
                nextchar !=self .state and nextchar !=escapedstate ):
                    self .token +=self .state
                self .token +=nextchar
                self .state =escapedstate
            elif self .state in ('a','c'):
                if not nextchar :
                    self .state =None
                    break
                elif nextchar in self .whitespace :
                    if self .debug >=2 :
                        print ("shlex: I see whitespace in word state")
                    self .state =' '
                    if self .token or (self .posix and quoted ):
                        break
                    else :
                        continue
                elif nextchar in self .commenters :
                    self .instream .readline ()
                    self .lineno +=1
                    if self .posix :
                        self .state =' '
                        if self .token or (self .posix and quoted ):
                            break
                        else :
                            continue
                elif self .state =='c':
                    if nextchar in self .punctuation_chars :
                        self .token +=nextchar
                    else :
                        if nextchar not in self .whitespace :
                            self ._pushback_chars .append (nextchar )
                        self .state =' '
                        break
                elif self .posix and nextchar in self .quotes :
                    self .state =nextchar
                elif self .posix and nextchar in self .escape :
                    escapedstate ='a'
                    self .state =nextchar
                elif (nextchar in self .wordchars or nextchar in self .quotes
                or (self .whitespace_split and
                nextchar not in self .punctuation_chars )):
                    self .token +=nextchar
                else :
                    if self .punctuation_chars :
                        self ._pushback_chars .append (nextchar )
                    else :
                        self .pushback .appendleft (nextchar )
                    if self .debug >=2 :
                        print ("shlex: I see punctuation in word state")
                    self .state =' '
                    if self .token or (self .posix and quoted ):
                        break
                    else :
                        continue
        result =self .token
        self .token =''
        if self .posix and not quoted and result =='':
            result =None
        if self .debug >1 :
            if result :
                print ("shlex: raw token="+repr (result ))
            else :
                print ("shlex: raw token=EOF")
        return result
    def sourcehook (self ,newfile ):
        if newfile [0 ]=='"':
            newfile =newfile [1 :-1 ]
        if isinstance (self .infile ,str )and not os .path .isabs (newfile ):
            newfile =os .path .join (os .path .dirname (self .infile ),newfile )
        return (newfile ,open (newfile ,"r"))
    def error_leader (self ,infile =None ,lineno =None ):
        if infile is None :
            infile =self .infile
        if lineno is None :
            lineno =self .lineno
        return "\"%s\", line %d: "%(infile ,lineno )
    def __iter__ (self ):
        return self
    def __next__ (self ):
        token =self .get_token ()
        if token ==self .eof :
            raise StopIteration
        return token
def split (s ,comments =False ,posix =True ):
    if s is None :
        raise ValueError ("s argument must not be None")
    lex =shlex (s ,posix =posix )
    lex .whitespace_split =True
    if not comments :
        lex .commenters =''
    return list (lex )
def join (split_command ):
    return ' '.join (quote (arg )for arg in split_command )
_find_unsafe =re .compile (r'[^\w@%+=:,./-]',re .ASCII ).search
def quote (s ):
    if not s :
        return "''"
    if _find_unsafe (s )is None :
        return s
    return "'"+s .replace ("'","'\"'\"'")+"'"
def _print_tokens (lexer ):
    while tt :=lexer .get_token ():
        print ("Token: "+repr (tt ))
if __name__ =='__main__':
    if len (sys .argv )==1 :
        _print_tokens (shlex ())
    else :
        fn =sys .argv [1 ]
        with open (fn )as f :
            _print_tokens (shlex (f ,fn ))
import re
import types
from _csv import Error ,writer ,reader ,register_dialect ,unregister_dialect ,get_dialect ,list_dialects ,field_size_limit ,QUOTE_MINIMAL ,QUOTE_ALL ,QUOTE_NONNUMERIC ,QUOTE_NONE ,QUOTE_STRINGS ,QUOTE_NOTNULL
from _csv import Dialect as _Dialect
from io import StringIO
__all__ =["QUOTE_MINIMAL","QUOTE_ALL","QUOTE_NONNUMERIC","QUOTE_NONE",
"","QUOTE_NOTNULL",
"","Dialect","excel","excel_tab",
"","reader","writer",
"","get_dialect","list_dialects","Sniffer",
"","DictReader","DictWriter",
""]
__version__ ="1.0"
class Dialect :
    _name =""
    _valid =False
    delimiter =None
    quotechar =None
    escapechar =None
    doublequote =None
    skipinitialspace =None
    lineterminator =None
    quoting =None
    def __init__ (self ):
        if self .__class__ !=Dialect :
            self ._valid =True
        self ._validate ()
    def _validate (self ):
        try :
            _Dialect (self )
        except TypeError as e :
            raise Error (str (e ))from None
class excel (Dialect ):
    delimiter =','
    quotechar ='"'
    doublequote =True
    skipinitialspace =False
    lineterminator ='\r\n'
    quoting =QUOTE_MINIMAL
register_dialect ("excel",excel )
class excel_tab (excel ):
    delimiter ='\t'
register_dialect ("excel-tab",excel_tab )
class unix_dialect (Dialect ):
    delimiter =','
    quotechar ='"'
    doublequote =True
    skipinitialspace =False
    lineterminator ='\n'
    quoting =QUOTE_ALL
register_dialect ("unix",unix_dialect )
class DictReader :
    def __init__ (self ,f ,fieldnames =None ,restkey =None ,restval =None ,
    dialect ="excel",*args ,**kwds ):
        if fieldnames is not None and iter (fieldnames )is fieldnames :
            fieldnames =list (fieldnames )
        self ._fieldnames =fieldnames
        self .restkey =restkey
        self .restval =restval
        self .reader =reader (f ,dialect ,*args ,**kwds )
        self .dialect =dialect
        self .line_num =0
    def __iter__ (self ):
        return self
    @property
    def fieldnames (self ):
        if self ._fieldnames is None :
            try :
                self ._fieldnames =next (self .reader )
            except StopIteration :
                pass
        self .line_num =self .reader .line_num
        return self ._fieldnames
    @fieldnames .setter
    def fieldnames (self ,value ):
        self ._fieldnames =value
    def __next__ (self ):
        if self .line_num ==0 :
            self .fieldnames
        row =next (self .reader )
        self .line_num =self .reader .line_num
        while row ==[]:
            row =next (self .reader )
        d =dict (zip (self .fieldnames ,row ))
        lf =len (self .fieldnames )
        lr =len (row )
        if lf <lr :
            d [self .restkey ]=row [lf :]
        elif lf >lr :
            for key in self .fieldnames [lr :]:
                d [key ]=self .restval
        return d
    __class_getitem__ =classmethod (types .GenericAlias )
class DictWriter :
    def __init__ (self ,f ,fieldnames ,restval ="",extrasaction ="raise",
    dialect ="excel",*args ,**kwds ):
        if fieldnames is not None and iter (fieldnames )is fieldnames :
            fieldnames =list (fieldnames )
        self .fieldnames =fieldnames
        self .restval =restval
        extrasaction =extrasaction .lower ()
        if extrasaction not in ("raise","ignore"):
            raise ValueError ("extrasaction (%s) must be 'raise' or 'ignore'"
            %extrasaction )
        self .extrasaction =extrasaction
        self .writer =writer (f ,dialect ,*args ,**kwds )
    def writeheader (self ):
        header =dict (zip (self .fieldnames ,self .fieldnames ))
        return self .writerow (header )
    def _dict_to_list (self ,rowdict ):
        if self .extrasaction =="raise":
            wrong_fields =rowdict .keys ()-self .fieldnames
            if wrong_fields :
                raise ValueError ("dict contains fields not in fieldnames: "
                +", ".join ([repr (x )for x in wrong_fields ]))
        return (rowdict .get (key ,self .restval )for key in self .fieldnames )
    def writerow (self ,rowdict ):
        return self .writer .writerow (self ._dict_to_list (rowdict ))
    def writerows (self ,rowdicts ):
        return self .writer .writerows (map (self ._dict_to_list ,rowdicts ))
    __class_getitem__ =classmethod (types .GenericAlias )
class Sniffer :
    def __init__ (self ):
        self .preferred =[',','\t',';',' ',':']
    def sniff (self ,sample ,delimiters =None ):
        sample =sample .replace ('\r\n','\n').replace ('\r','\n')
        quotechar ,doublequote ,delimiter ,skipinitialspace =self ._guess_quote_and_delimiter (sample ,delimiters )
        if not delimiter :
            delimiter ,skipinitialspace =self ._guess_delimiter (sample ,
            delimiters )
        if not delimiter :
            raise Error ("Could not determine delimiter")
        class dialect (Dialect ):
            _name ="sniffed"
            lineterminator ='\r\n'
            quoting =QUOTE_MINIMAL
        dialect .doublequote =doublequote
        dialect .delimiter =delimiter
        dialect .quotechar =quotechar or '"'
        dialect .skipinitialspace =skipinitialspace
        return dialect
    def _guess_quote_and_delimiter (self ,data ,delimiters ):
        body =r'(?:(?P=quote){2}|(?!(?P=quote)).)*+'
        matches =[]
        for restr in (r'(?P<delim>[^\w\n"\'])(?P<space> ?)(?P<quote>["\'])%s(?P=quote)(?P=delim)',
        "",
        "",
        ""):
            regexp =re .compile (restr %body ,re .DOTALL |re .MULTILINE )
            matches =regexp .findall (data )
            if matches :
                break
        if not matches :
            return ('',False ,None ,0 )
        quotes ={}
        delims ={}
        spaces =0
        groupindex =regexp .groupindex
        for m in matches :
            n =groupindex ['quote']-1
            key =m [n ]
            if key :
                quotes [key ]=quotes .get (key ,0 )+1
            try :
                n =groupindex ['delim']-1
                key =m [n ]
            except KeyError :
                continue
            if key and (delimiters is None or key in delimiters ):
                delims [key ]=delims .get (key ,0 )+1
            try :
                n =groupindex ['space']-1
            except KeyError :
                continue
            if m [n ]:
                spaces +=1
        quotechar =max (quotes ,key =quotes .get )
        if delims :
            delim =max (delims ,key =delims .get )
            skipinitialspace =delims [delim ]==spaces
            if delim =='\n':
                delim =''
        else :
            delim =''
            skipinitialspace =0
        doublequote =False
        if delim :
            dq_regexp =re .compile (
            %{'delim':re .escape (delim ),'quote':quotechar ,
            "":' *+'if delim !=' 'else ''},
            re .MULTILINE )
            dquotechar =quotechar *2
            doublequote =any (dquotechar in m [1 ]
            for m in dq_regexp .finditer (data ))
        return (quotechar ,doublequote ,delim ,skipinitialspace )
    def _guess_delimiter (self ,data ,delimiters ):
        data =list (filter (None ,data .split ('\n')))
        ascii =[chr (c )for c in range (127 )]
        chunkLength =min (10 ,len (data ))
        iteration =0
        charFrequency ={}
        modes ={}
        delims ={}
        start ,end =0 ,chunkLength
        while start <len (data ):
            iteration +=1
            for line in data [start :end ]:
                for char in ascii :
                    metaFrequency =charFrequency .get (char ,{})
                    freq =line .count (char )
                    metaFrequency [freq ]=metaFrequency .get (freq ,0 )+1
                    charFrequency [char ]=metaFrequency
            for char in charFrequency .keys ():
                items =list (charFrequency [char ].items ())
                if len (items )==1 and items [0 ][0 ]==0 :
                    continue
                if len (items )>1 :
                    modes [char ]=max (items ,key =lambda x :x [1 ])
                    items .remove (modes [char ])
                    modes [char ]=(modes [char ][0 ],modes [char ][1 ]
                    -sum (item [1 ]for item in items ))
                else :
                    modes [char ]=items [0 ]
            modeList =modes .items ()
            total =float (min (chunkLength *iteration ,len (data )))
            consistency =1.0
            threshold =0.9
            while len (delims )==0 and consistency >=threshold :
                for k ,v in modeList :
                    if v [0 ]>0 and v [1 ]>0 :
                        if ((v [1 ]/total )>=consistency and
                        (delimiters is None or k in delimiters )):
                            delims [k ]=v
                consistency -=0.01
            if len (delims )==1 :
                delim =list (delims .keys ())[0 ]
                skipinitialspace =(data [0 ].count (delim )==
                data [0 ].count ("%c "%delim ))
                return (delim ,skipinitialspace )
            start =end
            end +=chunkLength
        if not delims :
            return ('',0 )
        if len (delims )>1 :
            for d in self .preferred :
                if d in delims .keys ():
                    skipinitialspace =(data [0 ].count (d )==
                    data [0 ].count ("%c "%d ))
                    return (d ,skipinitialspace )
        items =[(v ,k )for (k ,v )in delims .items ()]
        items .sort ()
        delim =items [-1 ][1 ]
        skipinitialspace =(data [0 ].count (delim )==
        data [0 ].count ("%c "%delim ))
        return (delim ,skipinitialspace )
    def has_header (self ,sample ):
        rdr =reader (StringIO (sample ),self .sniff (sample ))
        header =next (rdr )
        columns =len (header )
        columnTypes ={}
        for i in range (columns ):columnTypes [i ]=None
        checked =0
        for row in rdr :
            if checked >20 :
                break
            checked +=1
            if len (row )!=columns :
                continue
            for col in list (columnTypes .keys ()):
                thisType =complex
                try :
                    thisType (row [col ])
                except (ValueError ,OverflowError ):
                    thisType =len (row [col ])
                if thisType !=columnTypes [col ]:
                    if columnTypes [col ]is None :
                        columnTypes [col ]=thisType
                    else :
                        del columnTypes [col ]
        hasHeader =0
        for col ,colType in columnTypes .items ():
            if isinstance (colType ,int ):
                if len (header [col ])!=colType :
                    hasHeader +=1
                else :
                    hasHeader -=1
            else :
                try :
                    colType (header [col ])
                except (ValueError ,TypeError ):
                    hasHeader +=1
                else :
                    hasHeader -=1
        return hasHeader >0
__version__ ='1.0'
import functools
IPV4LENGTH =32
IPV6LENGTH =128
class AddressValueError (ValueError ):
class NetmaskValueError (ValueError ):
def ip_address (address ):
    try :
        return IPv4Address (address )
    except (AddressValueError ,NetmaskValueError ):
        pass
    try :
        return IPv6Address (address )
    except (AddressValueError ,NetmaskValueError ):
        pass
    raise ValueError (f'{address !r } does not appear to be an IPv4 or IPv6 address')
def ip_network (address ,strict =True ):
    try :
        return IPv4Network (address ,strict )
    except (AddressValueError ,NetmaskValueError ):
        pass
    try :
        return IPv6Network (address ,strict )
    except (AddressValueError ,NetmaskValueError ):
        pass
    raise ValueError (f'{address !r } does not appear to be an IPv4 or IPv6 network')
def ip_interface (address ):
    try :
        return IPv4Interface (address )
    except (AddressValueError ,NetmaskValueError ):
        pass
    try :
        return IPv6Interface (address )
    except (AddressValueError ,NetmaskValueError ):
        pass
    raise ValueError (f'{address !r } does not appear to be an IPv4 or IPv6 interface')
def v4_int_to_packed (address ):
    try :
        return address .to_bytes (4 )
    except OverflowError :
        raise ValueError ("Address negative or too large for IPv4")
def v6_int_to_packed (address ):
    try :
        return address .to_bytes (16 )
    except OverflowError :
        raise ValueError ("Address negative or too large for IPv6")
def _split_optional_netmask (address ):
    addr =str (address ).split ('/')
    if len (addr )>2 :
        raise AddressValueError (f"Only one '/' permitted in {address !r }")
    return addr
def _find_address_range (addresses ):
    it =iter (addresses )
    first =last =next (it )
    for ip in it :
        if ip ._ip !=last ._ip +1 :
            yield first ,last
            first =ip
        last =ip
    yield first ,last
def _count_righthand_zero_bits (number ,bits ):
    if number ==0 :
        return bits
    return min (bits ,(~number &(number -1 )).bit_length ())
def summarize_address_range (first ,last ):
    if (not (isinstance (first ,_BaseAddress )and
    isinstance (last ,_BaseAddress ))):
        raise TypeError ('first and last must be IP addresses, not networks')
    if first .version !=last .version :
        raise TypeError ("%s and %s are not of the same version"%(
        first ,last ))
    if first >last :
        raise ValueError ('last IP address must be greater than first')
    if first .version ==4 :
        ip =IPv4Network
    elif first .version ==6 :
        ip =IPv6Network
    else :
        raise ValueError ('unknown IP version')
    ip_bits =first ._max_prefixlen
    first_int =first ._ip
    last_int =last ._ip
    while first_int <=last_int :
        nbits =min (_count_righthand_zero_bits (first_int ,ip_bits ),
        (last_int -first_int +1 ).bit_length ()-1 )
        net =ip ((first_int ,ip_bits -nbits ))
        yield net
        first_int +=1 <<nbits
        if first_int -1 ==ip ._ALL_ONES :
            break
def _collapse_addresses_internal (addresses ):
    to_merge =list (addresses )
    subnets ={}
    while to_merge :
        net =to_merge .pop ()
        supernet =net .supernet ()
        existing =subnets .get (supernet )
        if existing is None :
            subnets [supernet ]=net
        elif existing !=net :
            del subnets [supernet ]
            to_merge .append (supernet )
    last =None
    for net in sorted (subnets .values ()):
        if last is not None :
            if last .broadcast_address >=net .broadcast_address :
                continue
        yield net
        last =net
def collapse_addresses (addresses ):
    addrs =[]
    ips =[]
    nets =[]
    for ip in addresses :
        if isinstance (ip ,_BaseAddress ):
            if ips and ips [-1 ]._version !=ip ._version :
                raise TypeError ("%s and %s are not of the same version"%(
                ip ,ips [-1 ]))
            ips .append (ip )
        elif ip ._prefixlen ==ip ._max_prefixlen :
            if ips and ips [-1 ]._version !=ip ._version :
                raise TypeError ("%s and %s are not of the same version"%(
                ip ,ips [-1 ]))
            try :
                ips .append (ip .ip )
            except AttributeError :
                ips .append (ip .network_address )
        else :
            if nets and nets [-1 ]._version !=ip ._version :
                raise TypeError ("%s and %s are not of the same version"%(
                ip ,nets [-1 ]))
            nets .append (ip )
    ips =sorted (set (ips ))
    if ips :
        for first ,last in _find_address_range (ips ):
            addrs .extend (summarize_address_range (first ,last ))
    return _collapse_addresses_internal (addrs +nets )
def get_mixed_type_key (obj ):
    if isinstance (obj ,_BaseNetwork ):
        return obj ._get_networks_key ()
    elif isinstance (obj ,_BaseAddress ):
        return obj ._get_address_key ()
    return NotImplemented
class _IPAddressBase :
    __slots__ =()
    @property
    def exploded (self ):
        return self ._explode_shorthand_ip_string ()
    @property
    def compressed (self ):
        return str (self )
    @property
    def reverse_pointer (self ):
        return self ._reverse_pointer ()
    @property
    def version (self ):
        msg ='%200s has no version specified'%(type (self ),)
        raise NotImplementedError (msg )
    def _check_int_address (self ,address ):
        if address <0 :
            msg ="%d (< 0) is not permitted as an IPv%d address"
            raise AddressValueError (msg %(address ,self ._version ))
        if address >self ._ALL_ONES :
            msg ="%d (>= 2**%d) is not permitted as an IPv%d address"
            raise AddressValueError (msg %(address ,self ._max_prefixlen ,
            self ._version ))
    def _check_packed_address (self ,address ,expected_len ):
        address_len =len (address )
        if address_len !=expected_len :
            msg ="%r (len %d != %d) is not permitted as an IPv%d address"
            raise AddressValueError (msg %(address ,address_len ,
            expected_len ,self ._version ))
    @classmethod
    def _ip_int_from_prefix (cls ,prefixlen ):
        return cls ._ALL_ONES ^(cls ._ALL_ONES >>prefixlen )
    @classmethod
    def _prefix_from_ip_int (cls ,ip_int ):
        trailing_zeroes =_count_righthand_zero_bits (ip_int ,
        cls ._max_prefixlen )
        prefixlen =cls ._max_prefixlen -trailing_zeroes
        leading_ones =ip_int >>trailing_zeroes
        all_ones =(1 <<prefixlen )-1
        if leading_ones !=all_ones :
            byteslen =cls ._max_prefixlen //8
            details =ip_int .to_bytes (byteslen ,'big')
            msg ='Netmask pattern %r mixes zeroes & ones'
            raise ValueError (msg %details )
        return prefixlen
    @classmethod
    def _report_invalid_netmask (cls ,netmask_str ):
        msg ='%r is not a valid netmask'%netmask_str
        raise NetmaskValueError (msg )from None
    @classmethod
    def _prefix_from_prefix_string (cls ,prefixlen_str ):
        if not (prefixlen_str .isascii ()and prefixlen_str .isdigit ()):
            cls ._report_invalid_netmask (prefixlen_str )
        try :
            prefixlen =int (prefixlen_str )
        except ValueError :
            cls ._report_invalid_netmask (prefixlen_str )
        if not (0 <=prefixlen <=cls ._max_prefixlen ):
            cls ._report_invalid_netmask (prefixlen_str )
        return prefixlen
    @classmethod
    def _prefix_from_ip_string (cls ,ip_str ):
        try :
            ip_int =cls ._ip_int_from_string (ip_str )
        except AddressValueError :
            cls ._report_invalid_netmask (ip_str )
        try :
            return cls ._prefix_from_ip_int (ip_int )
        except ValueError :
            pass
        ip_int ^=cls ._ALL_ONES
        try :
            return cls ._prefix_from_ip_int (ip_int )
        except ValueError :
            cls ._report_invalid_netmask (ip_str )
    @classmethod
    def _split_addr_prefix (cls ,address ):
        if isinstance (address ,(bytes ,int )):
            return address ,cls ._max_prefixlen
        if not isinstance (address ,tuple ):
            address =_split_optional_netmask (address )
        if len (address )>1 :
            return address
        return address [0 ],cls ._max_prefixlen
    def __reduce__ (self ):
        return self .__class__ ,(str (self ),)
_address_fmt_re =None
@functools .total_ordering
class _BaseAddress (_IPAddressBase ):
    __slots__ =()
    def __int__ (self ):
        return self ._ip
    def __eq__ (self ,other ):
        try :
            return (self ._ip ==other ._ip
            and self ._version ==other ._version )
        except AttributeError :
            return NotImplemented
    def __lt__ (self ,other ):
        if not isinstance (other ,_BaseAddress ):
            return NotImplemented
        if self ._version !=other ._version :
            raise TypeError ('%s and %s are not of the same version'%(
            self ,other ))
        if self ._ip !=other ._ip :
            return self ._ip <other ._ip
        return False
    def __add__ (self ,other ):
        if not isinstance (other ,int ):
            return NotImplemented
        return self .__class__ (int (self )+other )
    def __sub__ (self ,other ):
        if not isinstance (other ,int ):
            return NotImplemented
        return self .__class__ (int (self )-other )
    def __repr__ (self ):
        return '%s(%r)'%(self .__class__ .__name__ ,str (self ))
    def __str__ (self ):
        return str (self ._string_from_ip_int (self ._ip ))
    def __hash__ (self ):
        return hash (hex (int (self ._ip )))
    def _get_address_key (self ):
        return (self ._version ,self )
    def __reduce__ (self ):
        return self .__class__ ,(self ._ip ,)
    def __format__ (self ,fmt ):
        if not fmt or fmt [-1 ]=='s':
            return format (str (self ),fmt )
        global _address_fmt_re
        if _address_fmt_re is None :
            import re
            _address_fmt_re =re .compile ('(#?)(_?)([xbnX])')
        m =_address_fmt_re .fullmatch (fmt )
        if not m :
            return super ().__format__ (fmt )
        alternate ,grouping ,fmt_base =m .groups ()
        if fmt_base =='n':
            if self ._version ==4 :
                fmt_base ='b'
            else :
                fmt_base ='x'
        if fmt_base =='b':
            padlen =self ._max_prefixlen
        else :
            padlen =self ._max_prefixlen //4
        if grouping :
            padlen +=padlen //4 -1
        if alternate :
            padlen +=2
        return format (int (self ),f'{alternate }0{padlen }{grouping }{fmt_base }')
@functools .total_ordering
class _BaseNetwork (_IPAddressBase ):
    def __repr__ (self ):
        return '%s(%r)'%(self .__class__ .__name__ ,str (self ))
    def __str__ (self ):
        return '%s/%d'%(self .network_address ,self .prefixlen )
    def hosts (self ):
        network =int (self .network_address )
        broadcast =int (self .broadcast_address )
        for x in range (network +1 ,broadcast ):
            yield self ._address_class (x )
    def __iter__ (self ):
        network =int (self .network_address )
        broadcast =int (self .broadcast_address )
        for x in range (network ,broadcast +1 ):
            yield self ._address_class (x )
    def __getitem__ (self ,n ):
        network =int (self .network_address )
        broadcast =int (self .broadcast_address )
        if n >=0 :
            if network +n >broadcast :
                raise IndexError ('address out of range')
            return self ._address_class (network +n )
        else :
            n +=1
            if broadcast +n <network :
                raise IndexError ('address out of range')
            return self ._address_class (broadcast +n )
    def __lt__ (self ,other ):
        if not isinstance (other ,_BaseNetwork ):
            return NotImplemented
        if self ._version !=other ._version :
            raise TypeError ('%s and %s are not of the same version'%(
            self ,other ))
        if self .network_address !=other .network_address :
            return self .network_address <other .network_address
        if self .netmask !=other .netmask :
            return self .netmask <other .netmask
        return False
    def __eq__ (self ,other ):
        try :
            return (self ._version ==other ._version and
            self .network_address ==other .network_address and
            int (self .netmask )==int (other .netmask ))
        except AttributeError :
            return NotImplemented
    def __hash__ (self ):
        return hash ((int (self .network_address ),int (self .netmask )))
    def __contains__ (self ,other ):
        if self ._version !=other ._version :
            return False
        if isinstance (other ,_BaseNetwork ):
            return False
        else :
            return other ._ip &self .netmask ._ip ==self .network_address ._ip
    def overlaps (self ,other ):
        return self .network_address in other or (
        self .broadcast_address in other or (
        other .network_address in self or (
        other .broadcast_address in self )))
    @functools .cached_property
    def broadcast_address (self ):
        return self ._address_class (int (self .network_address )|
        int (self .hostmask ))
    @functools .cached_property
    def hostmask (self ):
        return self ._address_class (int (self .netmask )^self ._ALL_ONES )
    @property
    def with_prefixlen (self ):
        return '%s/%d'%(self .network_address ,self ._prefixlen )
    @property
    def with_netmask (self ):
        return '%s/%s'%(self .network_address ,self .netmask )
    @property
    def with_hostmask (self ):
        return '%s/%s'%(self .network_address ,self .hostmask )
    @property
    def num_addresses (self ):
        return int (self .broadcast_address )-int (self .network_address )+1
    @property
    def _address_class (self ):
        msg ='%200s has no associated address class'%(type (self ),)
        raise NotImplementedError (msg )
    @property
    def prefixlen (self ):
        return self ._prefixlen
    def address_exclude (self ,other ):
        if not self ._version ==other ._version :
            raise TypeError ("%s and %s are not of the same version"%(
            self ,other ))
        if not isinstance (other ,_BaseNetwork ):
            raise TypeError ("%s is not a network object"%other )
        if not other .subnet_of (self ):
            raise ValueError ('%s not contained in %s'%(other ,self ))
        if other ==self :
            return
        other =other .__class__ ('%s/%s'%(other .network_address ,
        other .prefixlen ))
        s1 ,s2 =self .subnets ()
        while s1 !=other and s2 !=other :
            if other .subnet_of (s1 ):
                yield s2
                s1 ,s2 =s1 .subnets ()
            elif other .subnet_of (s2 ):
                yield s1
                s1 ,s2 =s2 .subnets ()
            else :
                raise AssertionError ('Error performing exclusion: '
                ""%
                (s1 ,s2 ,other ))
        if s1 ==other :
            yield s2
        elif s2 ==other :
            yield s1
        else :
            raise AssertionError ('Error performing exclusion: '
            ""%
            (s1 ,s2 ,other ))
    def compare_networks (self ,other ):
        if self ._version !=other ._version :
            raise TypeError ('%s and %s are not of the same type'%(
            self ,other ))
        if self .network_address <other .network_address :
            return -1
        if self .network_address >other .network_address :
            return 1
        if self .netmask <other .netmask :
            return -1
        if self .netmask >other .netmask :
            return 1
        return 0
    def _get_networks_key (self ):
        return (self ._version ,self .network_address ,self .netmask )
    def subnets (self ,prefixlen_diff =1 ,new_prefix =None ):
        if self ._prefixlen ==self ._max_prefixlen :
            yield self
            return
        if new_prefix is not None :
            if new_prefix <self ._prefixlen :
                raise ValueError ('new prefix must be longer')
            if prefixlen_diff !=1 :
                raise ValueError ('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff =new_prefix -self ._prefixlen
        if prefixlen_diff <0 :
            raise ValueError ('prefix length diff must be > 0')
        new_prefixlen =self ._prefixlen +prefixlen_diff
        if new_prefixlen >self ._max_prefixlen :
            raise ValueError (
            ""%(
            new_prefixlen ,self ))
        start =int (self .network_address )
        end =int (self .broadcast_address )+1
        step =(int (self .hostmask )+1 )>>prefixlen_diff
        for new_addr in range (start ,end ,step ):
            current =self .__class__ ((new_addr ,new_prefixlen ))
            yield current
    def supernet (self ,prefixlen_diff =1 ,new_prefix =None ):
        if self ._prefixlen ==0 :
            return self
        if new_prefix is not None :
            if new_prefix >self ._prefixlen :
                raise ValueError ('new prefix must be shorter')
            if prefixlen_diff !=1 :
                raise ValueError ('cannot set prefixlen_diff and new_prefix')
            prefixlen_diff =self ._prefixlen -new_prefix
        new_prefixlen =self .prefixlen -prefixlen_diff
        if new_prefixlen <0 :
            raise ValueError (
            ""%
            (self .prefixlen ,prefixlen_diff ))
        return self .__class__ ((
        int (self .network_address )&(int (self .netmask )<<prefixlen_diff ),
        new_prefixlen
        ))
    @property
    def is_multicast (self ):
        return (self .network_address .is_multicast and
        self .broadcast_address .is_multicast )
    @staticmethod
    def _is_subnet_of (a ,b ):
        try :
            if a ._version !=b ._version :
                raise TypeError (f"{a } and {b } are not of the same version")
            return (b .network_address <=a .network_address and
            b .broadcast_address >=a .broadcast_address )
        except AttributeError :
            raise TypeError (f"Unable to test subnet containment "
            f"between {a } and {b }")
    def subnet_of (self ,other ):
        return self ._is_subnet_of (self ,other )
    def supernet_of (self ,other ):
        return self ._is_subnet_of (other ,self )
    @property
    def is_reserved (self ):
        return (self .network_address .is_reserved and
        self .broadcast_address .is_reserved )
    @property
    def is_link_local (self ):
        return (self .network_address .is_link_local and
        self .broadcast_address .is_link_local )
    @property
    def is_private (self ):
        return any (self .network_address in priv_network and
        self .broadcast_address in priv_network
        for priv_network in self ._constants ._private_networks )and all (
        self .network_address not in network and
        self .broadcast_address not in network
        for network in self ._constants ._private_networks_exceptions
        )
    @property
    def is_global (self ):
        return not self .is_private
    @property
    def is_unspecified (self ):
        return (self .network_address .is_unspecified and
        self .broadcast_address .is_unspecified )
    @property
    def is_loopback (self ):
        return (self .network_address .is_loopback and
        self .broadcast_address .is_loopback )
class _BaseConstants :
    _private_networks =[]
_BaseNetwork ._constants =_BaseConstants
class _BaseV4 :
    __slots__ =()
    _version =4
    _ALL_ONES =(2 **IPV4LENGTH )-1
    _max_prefixlen =IPV4LENGTH
    _netmask_cache ={}
    def _explode_shorthand_ip_string (self ):
        return str (self )
    @classmethod
    def _make_netmask (cls ,arg ):
        if arg not in cls ._netmask_cache :
            if isinstance (arg ,int ):
                prefixlen =arg
                if not (0 <=prefixlen <=cls ._max_prefixlen ):
                    cls ._report_invalid_netmask (prefixlen )
            else :
                try :
                    prefixlen =cls ._prefix_from_prefix_string (arg )
                except NetmaskValueError :
                    prefixlen =cls ._prefix_from_ip_string (arg )
            netmask =IPv4Address (cls ._ip_int_from_prefix (prefixlen ))
            cls ._netmask_cache [arg ]=netmask ,prefixlen
        return cls ._netmask_cache [arg ]
    @classmethod
    def _ip_int_from_string (cls ,ip_str ):
        if not ip_str :
            raise AddressValueError ('Address cannot be empty')
        octets =ip_str .split ('.')
        if len (octets )!=4 :
            raise AddressValueError ("Expected 4 octets in %r"%ip_str )
        try :
            return int .from_bytes (map (cls ._parse_octet ,octets ),'big')
        except ValueError as exc :
            raise AddressValueError ("%s in %r"%(exc ,ip_str ))from None
    @classmethod
    def _parse_octet (cls ,octet_str ):
        if not octet_str :
            raise ValueError ("Empty octet not permitted")
        if not (octet_str .isascii ()and octet_str .isdigit ()):
            msg ="Only decimal digits permitted in %r"
            raise ValueError (msg %octet_str )
        if len (octet_str )>3 :
            msg ="At most 3 characters permitted in %r"
            raise ValueError (msg %octet_str )
        if octet_str !='0'and octet_str [0 ]=='0':
            msg ="Leading zeros are not permitted in %r"
            raise ValueError (msg %octet_str )
        octet_int =int (octet_str ,10 )
        if octet_int >255 :
            raise ValueError ("Octet %d (> 255) not permitted"%octet_int )
        return octet_int
    @classmethod
    def _string_from_ip_int (cls ,ip_int ):
        return '.'.join (map (str ,ip_int .to_bytes (4 ,'big')))
    def _reverse_pointer (self ):
        reverse_octets =str (self ).split ('.')[::-1 ]
        return '.'.join (reverse_octets )+'.in-addr.arpa'
    @property
    def max_prefixlen (self ):
        return self ._max_prefixlen
    @property
    def version (self ):
        return self ._version
class IPv4Address (_BaseV4 ,_BaseAddress ):
    __slots__ =('_ip','__weakref__')
    def __init__ (self ,address ):
        if isinstance (address ,int ):
            self ._check_int_address (address )
            self ._ip =address
            return
        if isinstance (address ,bytes ):
            self ._check_packed_address (address ,4 )
            self ._ip =int .from_bytes (address )
            return
        addr_str =str (address )
        if '/'in addr_str :
            raise AddressValueError (f"Unexpected '/' in {address !r }")
        self ._ip =self ._ip_int_from_string (addr_str )
    @property
    def packed (self ):
        return v4_int_to_packed (self ._ip )
    @property
    def is_reserved (self ):
        return self in self ._constants ._reserved_network
    @property
    @functools .lru_cache ()
    def is_private (self ):
        return (
        any (self in net for net in self ._constants ._private_networks )
        and all (self not in net for net in self ._constants ._private_networks_exceptions )
        )
    @property
    @functools .lru_cache ()
    def is_global (self ):
        return self not in self ._constants ._public_network and not self .is_private
    @property
    def is_multicast (self ):
        return self in self ._constants ._multicast_network
    @property
    def is_unspecified (self ):
        return self ==self ._constants ._unspecified_address
    @property
    def is_loopback (self ):
        return self in self ._constants ._loopback_network
    @property
    def is_link_local (self ):
        return self in self ._constants ._linklocal_network
    @property
    def ipv6_mapped (self ):
        return IPv6Address (f'::ffff:{self }')
class IPv4Interface (IPv4Address ):
    def __init__ (self ,address ):
        addr ,mask =self ._split_addr_prefix (address )
        IPv4Address .__init__ (self ,addr )
        self .network =IPv4Network ((addr ,mask ),strict =False )
        self .netmask =self .network .netmask
        self ._prefixlen =self .network ._prefixlen
    @functools .cached_property
    def hostmask (self ):
        return self .network .hostmask
    def __str__ (self ):
        return '%s/%d'%(self ._string_from_ip_int (self ._ip ),
        self ._prefixlen )
    def __eq__ (self ,other ):
        address_equal =IPv4Address .__eq__ (self ,other )
        if address_equal is NotImplemented or not address_equal :
            return address_equal
        try :
            return self .network ==other .network
        except AttributeError :
            return False
    def __lt__ (self ,other ):
        address_less =IPv4Address .__lt__ (self ,other )
        if address_less is NotImplemented :
            return NotImplemented
        try :
            return (self .network <other .network or
            self .network ==other .network and address_less )
        except AttributeError :
            return False
    def __hash__ (self ):
        return hash ((self ._ip ,self ._prefixlen ,int (self .network .network_address )))
    __reduce__ =_IPAddressBase .__reduce__
    @property
    def ip (self ):
        return IPv4Address (self ._ip )
    @property
    def with_prefixlen (self ):
        return '%s/%s'%(self ._string_from_ip_int (self ._ip ),
        self ._prefixlen )
    @property
    def with_netmask (self ):
        return '%s/%s'%(self ._string_from_ip_int (self ._ip ),
        self .netmask )
    @property
    def with_hostmask (self ):
        return '%s/%s'%(self ._string_from_ip_int (self ._ip ),
        self .hostmask )
class IPv4Network (_BaseV4 ,_BaseNetwork ):
    _address_class =IPv4Address
    def __init__ (self ,address ,strict =True ):
        addr ,mask =self ._split_addr_prefix (address )
        self .network_address =IPv4Address (addr )
        self .netmask ,self ._prefixlen =self ._make_netmask (mask )
        packed =int (self .network_address )
        if packed &int (self .netmask )!=packed :
            if strict :
                raise ValueError ('%s has host bits set'%self )
            else :
                self .network_address =IPv4Address (packed &
                int (self .netmask ))
        if self ._prefixlen ==(self ._max_prefixlen -1 ):
            self .hosts =self .__iter__
        elif self ._prefixlen ==(self ._max_prefixlen ):
            self .hosts =lambda :iter ((IPv4Address (addr ),))
    @property
    @functools .lru_cache ()
    def is_global (self ):
        return (not (self .network_address in IPv4Network ('100.64.0.0/10')and
        self .broadcast_address in IPv4Network ('100.64.0.0/10'))and
        not self .is_private )
class _IPv4Constants :
    _linklocal_network =IPv4Network ('169.254.0.0/16')
    _loopback_network =IPv4Network ('127.0.0.0/8')
    _multicast_network =IPv4Network ('224.0.0.0/4')
    _public_network =IPv4Network ('100.64.0.0/10')
    _private_networks =[
    IPv4Network ('0.0.0.0/8'),
    IPv4Network ('10.0.0.0/8'),
    IPv4Network ('127.0.0.0/8'),
    IPv4Network ('169.254.0.0/16'),
    IPv4Network ('172.16.0.0/12'),
    IPv4Network ('192.0.0.0/24'),
    IPv4Network ('192.0.0.170/31'),
    IPv4Network ('192.0.2.0/24'),
    IPv4Network ('192.168.0.0/16'),
    IPv4Network ('198.18.0.0/15'),
    IPv4Network ('198.51.100.0/24'),
    IPv4Network ('203.0.113.0/24'),
    IPv4Network ('240.0.0.0/4'),
    IPv4Network ('255.255.255.255/32'),
    ]
    _private_networks_exceptions =[
    IPv4Network ('192.0.0.9/32'),
    IPv4Network ('192.0.0.10/32'),
    ]
    _reserved_network =IPv4Network ('240.0.0.0/4')
    _unspecified_address =IPv4Address ('0.0.0.0')
IPv4Address ._constants =_IPv4Constants
IPv4Network ._constants =_IPv4Constants
class _BaseV6 :
    __slots__ =()
    _version =6
    _ALL_ONES =(2 **IPV6LENGTH )-1
    _HEXTET_COUNT =8
    _HEX_DIGITS =frozenset ('0123456789ABCDEFabcdef')
    _max_prefixlen =IPV6LENGTH
    _netmask_cache ={}
    @classmethod
    def _make_netmask (cls ,arg ):
        if arg not in cls ._netmask_cache :
            if isinstance (arg ,int ):
                prefixlen =arg
                if not (0 <=prefixlen <=cls ._max_prefixlen ):
                    cls ._report_invalid_netmask (prefixlen )
            else :
                prefixlen =cls ._prefix_from_prefix_string (arg )
            netmask =IPv6Address (cls ._ip_int_from_prefix (prefixlen ))
            cls ._netmask_cache [arg ]=netmask ,prefixlen
        return cls ._netmask_cache [arg ]
    @classmethod
    def _ip_int_from_string (cls ,ip_str ):
        if not ip_str :
            raise AddressValueError ('Address cannot be empty')
        if len (ip_str )>45 :
            shorten =ip_str
            if len (shorten )>100 :
                shorten =f'{ip_str [:45 ]}({len (ip_str )-90 } chars elided){ip_str [-45 :]}'
            raise AddressValueError (f"At most 45 characters expected in "
            f"{shorten !r }")
        _max_parts =cls ._HEXTET_COUNT +1
        parts =ip_str .split (':',maxsplit =_max_parts )
        _min_parts =3
        if len (parts )<_min_parts :
            msg ="At least %d parts expected in %r"%(_min_parts ,ip_str )
            raise AddressValueError (msg )
        if '.'in parts [-1 ]:
            try :
                ipv4_int =IPv4Address (parts .pop ())._ip
            except AddressValueError as exc :
                raise AddressValueError ("%s in %r"%(exc ,ip_str ))from None
            parts .append ('%x'%((ipv4_int >>16 )&0xFFFF ))
            parts .append ('%x'%(ipv4_int &0xFFFF ))
        if len (parts )>_max_parts :
            msg ="At most %d colons permitted in %r"%(_max_parts -1 ,ip_str )
            raise AddressValueError (msg )
        skip_index =None
        for i in range (1 ,len (parts )-1 ):
            if not parts [i ]:
                if skip_index is not None :
                    msg ="At most one '::' permitted in %r"%ip_str
                    raise AddressValueError (msg )
                skip_index =i
        if skip_index is not None :
            parts_hi =skip_index
            parts_lo =len (parts )-skip_index -1
            if not parts [0 ]:
                parts_hi -=1
                if parts_hi :
                    msg ="Leading ':' only permitted as part of '::' in %r"
                    raise AddressValueError (msg %ip_str )
            if not parts [-1 ]:
                parts_lo -=1
                if parts_lo :
                    msg ="Trailing ':' only permitted as part of '::' in %r"
                    raise AddressValueError (msg %ip_str )
            parts_skipped =cls ._HEXTET_COUNT -(parts_hi +parts_lo )
            if parts_skipped <1 :
                msg ="Expected at most %d other parts with '::' in %r"
                raise AddressValueError (msg %(cls ._HEXTET_COUNT -1 ,ip_str ))
        else :
            if len (parts )!=cls ._HEXTET_COUNT :
                msg ="Exactly %d parts expected without '::' in %r"
                raise AddressValueError (msg %(cls ._HEXTET_COUNT ,ip_str ))
            if not parts [0 ]:
                msg ="Leading ':' only permitted as part of '::' in %r"
                raise AddressValueError (msg %ip_str )
            if not parts [-1 ]:
                msg ="Trailing ':' only permitted as part of '::' in %r"
                raise AddressValueError (msg %ip_str )
            parts_hi =len (parts )
            parts_lo =0
            parts_skipped =0
        try :
            ip_int =0
            for i in range (parts_hi ):
                ip_int <<=16
                ip_int |=cls ._parse_hextet (parts [i ])
            ip_int <<=16 *parts_skipped
            for i in range (-parts_lo ,0 ):
                ip_int <<=16
                ip_int |=cls ._parse_hextet (parts [i ])
            return ip_int
        except ValueError as exc :
            raise AddressValueError ("%s in %r"%(exc ,ip_str ))from None
    @classmethod
    def _parse_hextet (cls ,hextet_str ):
        if not cls ._HEX_DIGITS .issuperset (hextet_str ):
            raise ValueError ("Only hex digits permitted in %r"%hextet_str )
        if len (hextet_str )>4 :
            msg ="At most 4 characters permitted in %r"
            raise ValueError (msg %hextet_str )
        return int (hextet_str ,16 )
    @classmethod
    def _compress_hextets (cls ,hextets ):
        best_doublecolon_start =-1
        best_doublecolon_len =0
        doublecolon_start =-1
        doublecolon_len =0
        for index ,hextet in enumerate (hextets ):
            if hextet =='0':
                doublecolon_len +=1
                if doublecolon_start ==-1 :
                    doublecolon_start =index
                if doublecolon_len >best_doublecolon_len :
                    best_doublecolon_len =doublecolon_len
                    best_doublecolon_start =doublecolon_start
            else :
                doublecolon_len =0
                doublecolon_start =-1
        if best_doublecolon_len >1 :
            best_doublecolon_end =(best_doublecolon_start +
            best_doublecolon_len )
            if best_doublecolon_end ==len (hextets ):
                hextets +=['']
            hextets [best_doublecolon_start :best_doublecolon_end ]=['']
            if best_doublecolon_start ==0 :
                hextets =['']+hextets
        return hextets
    @classmethod
    def _string_from_ip_int (cls ,ip_int =None ):
        if ip_int is None :
            ip_int =int (cls ._ip )
        if ip_int >cls ._ALL_ONES :
            raise ValueError ('IPv6 address is too large')
        hex_str ='%032x'%ip_int
        hextets =['%x'%int (hex_str [x :x +4 ],16 )for x in range (0 ,32 ,4 )]
        hextets =cls ._compress_hextets (hextets )
        return ':'.join (hextets )
    def _explode_shorthand_ip_string (self ):
        if isinstance (self ,IPv6Network ):
            ip_str =str (self .network_address )
        elif isinstance (self ,IPv6Interface ):
            ip_str =str (self .ip )
        else :
            ip_str =self ._string_from_ip_int (self ._ip )
        ip_int =self ._ip_int_from_string (ip_str )
        hex_str ='%032x'%ip_int
        exploded =':'.join ([hex_str [x :x +4 ]for x in range (0 ,32 ,4 )])
        if isinstance (self ,_BaseNetwork ):
            return '%s/%d'%(exploded ,self ._prefixlen )
        if self ._scope_id :
            exploded ='%s%%%s'%(exploded ,self ._scope_id )
        if isinstance (self ,IPv6Interface ):
            return '%s/%d'%(exploded ,self ._prefixlen )
        return exploded
    def _reverse_pointer (self ):
        reverse_chars =self .exploded [::-1 ].replace (':','')
        return '.'.join (reverse_chars )+'.ip6.arpa'
    @staticmethod
    def _split_scope_id (ip_str ):
        addr ,sep ,scope_id =ip_str .partition ('%')
        if not sep :
            scope_id =None
        elif not scope_id or '%'in scope_id :
            raise AddressValueError ('Invalid IPv6 address: "%r"'%ip_str )
        return addr ,scope_id
    @property
    def max_prefixlen (self ):
        return self ._max_prefixlen
    @property
    def version (self ):
        return self ._version
class IPv6Address (_BaseV6 ,_BaseAddress ):
    __slots__ =('_ip','_scope_id','__weakref__')
    def __init__ (self ,address ):
        if isinstance (address ,int ):
            self ._check_int_address (address )
            self ._ip =address
            self ._scope_id =None
            return
        if isinstance (address ,bytes ):
            self ._check_packed_address (address ,16 )
            self ._ip =int .from_bytes (address ,'big')
            self ._scope_id =None
            return
        addr_str =str (address )
        if '/'in addr_str :
            raise AddressValueError (f"Unexpected '/' in {address !r }")
        addr_str ,self ._scope_id =self ._split_scope_id (addr_str )
        self ._ip =self ._ip_int_from_string (addr_str )
    def _explode_shorthand_ip_string (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is None :
            return super ()._explode_shorthand_ip_string ()
        prefix_len =30
        raw_exploded_str =super ()._explode_shorthand_ip_string ()
        return f"{raw_exploded_str [:prefix_len ]}{ipv4_mapped !s }"
    def _reverse_pointer (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is None :
            return super ()._reverse_pointer ()
        prefix_len =30
        raw_exploded_str =super ()._explode_shorthand_ip_string ()[:prefix_len ]
        ipv4_int =ipv4_mapped ._ip
        reverse_chars =f"{raw_exploded_str }{ipv4_int :008x}"[::-1 ].replace (':','')
        return '.'.join (reverse_chars )+'.ip6.arpa'
    def _ipv4_mapped_ipv6_to_str (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is None :
            raise AddressValueError ("Can not apply to non-IPv4-mapped IPv6 address %s"%str (self ))
        high_order_bits =self ._ip >>32
        return "%s:%s"%(self ._string_from_ip_int (high_order_bits ),str (ipv4_mapped ))
    def __str__ (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is None :
            ip_str =super ().__str__ ()
        else :
            ip_str =self ._ipv4_mapped_ipv6_to_str ()
        return ip_str +'%'+self ._scope_id if self ._scope_id else ip_str
    def __hash__ (self ):
        return hash ((self ._ip ,self ._scope_id ))
    def __eq__ (self ,other ):
        address_equal =super ().__eq__ (other )
        if address_equal is NotImplemented :
            return NotImplemented
        if not address_equal :
            return False
        return self ._scope_id ==getattr (other ,'_scope_id',None )
    def __reduce__ (self ):
        return (self .__class__ ,(str (self ),))
    @property
    def scope_id (self ):
        return self ._scope_id
    @property
    def packed (self ):
        return v6_int_to_packed (self ._ip )
    @property
    def is_multicast (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_multicast
        return self in self ._constants ._multicast_network
    @property
    def is_reserved (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_reserved
        return any (self in x for x in self ._constants ._reserved_networks )
    @property
    def is_link_local (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_link_local
        return self in self ._constants ._linklocal_network
    @property
    def is_site_local (self ):
        return self in self ._constants ._sitelocal_network
    @property
    @functools .lru_cache ()
    def is_private (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_private
        return (
        any (self in net for net in self ._constants ._private_networks )
        and all (self not in net for net in self ._constants ._private_networks_exceptions )
        )
    @property
    def is_global (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_global
        return not self .is_private
    @property
    def is_unspecified (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_unspecified
        return self ._ip ==0
    @property
    def is_loopback (self ):
        ipv4_mapped =self .ipv4_mapped
        if ipv4_mapped is not None :
            return ipv4_mapped .is_loopback
        return self ._ip ==1
    @property
    def ipv4_mapped (self ):
        if (self ._ip >>32 )!=0xFFFF :
            return None
        return IPv4Address (self ._ip &0xFFFFFFFF )
    @property
    def teredo (self ):
        if (self ._ip >>96 )!=0x20010000 :
            return None
        return (IPv4Address ((self ._ip >>64 )&0xFFFFFFFF ),
        IPv4Address (~self ._ip &0xFFFFFFFF ))
    @property
    def sixtofour (self ):
        if (self ._ip >>112 )!=0x2002 :
            return None
        return IPv4Address ((self ._ip >>80 )&0xFFFFFFFF )
class IPv6Interface (IPv6Address ):
    def __init__ (self ,address ):
        addr ,mask =self ._split_addr_prefix (address )
        IPv6Address .__init__ (self ,addr )
        self .network =IPv6Network ((addr ,mask ),strict =False )
        self .netmask =self .network .netmask
        self ._prefixlen =self .network ._prefixlen
    @functools .cached_property
    def hostmask (self ):
        return self .network .hostmask
    def __str__ (self ):
        return '%s/%d'%(super ().__str__ (),
        self ._prefixlen )
    def __eq__ (self ,other ):
        address_equal =IPv6Address .__eq__ (self ,other )
        if address_equal is NotImplemented or not address_equal :
            return address_equal
        try :
            return self .network ==other .network
        except AttributeError :
            return False
    def __lt__ (self ,other ):
        address_less =IPv6Address .__lt__ (self ,other )
        if address_less is NotImplemented :
            return address_less
        try :
            return (self .network <other .network or
            self .network ==other .network and address_less )
        except AttributeError :
            return False
    def __hash__ (self ):
        return hash ((self ._ip ,self ._prefixlen ,int (self .network .network_address )))
    __reduce__ =_IPAddressBase .__reduce__
    @property
    def ip (self ):
        return IPv6Address (self ._ip )
    @property
    def with_prefixlen (self ):
        return '%s/%s'%(self ._string_from_ip_int (self ._ip ),
        self ._prefixlen )
    @property
    def with_netmask (self ):
        return '%s/%s'%(self ._string_from_ip_int (self ._ip ),
        self .netmask )
    @property
    def with_hostmask (self ):
        return '%s/%s'%(self ._string_from_ip_int (self ._ip ),
        self .hostmask )
    @property
    def is_unspecified (self ):
        return self ._ip ==0 and self .network .is_unspecified
    @property
    def is_loopback (self ):
        return super ().is_loopback and self .network .is_loopback
class IPv6Network (_BaseV6 ,_BaseNetwork ):
    _address_class =IPv6Address
    def __init__ (self ,address ,strict =True ):
        addr ,mask =self ._split_addr_prefix (address )
        self .network_address =IPv6Address (addr )
        self .netmask ,self ._prefixlen =self ._make_netmask (mask )
        packed =int (self .network_address )
        if packed &int (self .netmask )!=packed :
            if strict :
                raise ValueError ('%s has host bits set'%self )
            else :
                self .network_address =IPv6Address (packed &
                int (self .netmask ))
        if self ._prefixlen ==(self ._max_prefixlen -1 ):
            self .hosts =self .__iter__
        elif self ._prefixlen ==self ._max_prefixlen :
            self .hosts =lambda :iter ((IPv6Address (addr ),))
    def hosts (self ):
        network =int (self .network_address )
        broadcast =int (self .broadcast_address )
        for x in range (network +1 ,broadcast +1 ):
            yield self ._address_class (x )
    @property
    def is_site_local (self ):
        return (self .network_address .is_site_local and
        self .broadcast_address .is_site_local )
class _IPv6Constants :
    _linklocal_network =IPv6Network ('fe80::/10')
    _multicast_network =IPv6Network ('ff00::/8')
    _private_networks =[
    IPv6Network ('::1/128'),
    IPv6Network ('::/128'),
    IPv6Network ('::ffff:0:0/96'),
    IPv6Network ('64:ff9b:1::/48'),
    IPv6Network ('100::/64'),
    IPv6Network ('2001::/23'),
    IPv6Network ('2001:db8::/32'),
    IPv6Network ('2002::/16'),
    IPv6Network ('3fff::/20'),
    IPv6Network ('fc00::/7'),
    IPv6Network ('fe80::/10'),
    ]
    _private_networks_exceptions =[
    IPv6Network ('2001:1::1/128'),
    IPv6Network ('2001:1::2/128'),
    IPv6Network ('2001:3::/32'),
    IPv6Network ('2001:4:112::/48'),
    IPv6Network ('2001:20::/28'),
    IPv6Network ('2001:30::/28'),
    ]
    _reserved_networks =[
    IPv6Network ('::/8'),IPv6Network ('100::/8'),
    IPv6Network ('200::/7'),IPv6Network ('400::/6'),
    IPv6Network ('800::/5'),IPv6Network ('1000::/4'),
    IPv6Network ('4000::/3'),IPv6Network ('6000::/3'),
    IPv6Network ('8000::/3'),IPv6Network ('A000::/3'),
    IPv6Network ('C000::/3'),IPv6Network ('E000::/4'),
    IPv6Network ('F000::/5'),IPv6Network ('F800::/6'),
    IPv6Network ('FE00::/9'),
    ]
    _sitelocal_network =IPv6Network ('fec0::/10')
IPv6Address ._constants =_IPv6Constants
IPv6Network ._constants =_IPv6Constants
import re
__all__ =['TextWrapper','wrap','fill','dedent','indent','shorten']
_whitespace ='\t\n\x0b\x0c\r '
class TextWrapper :
    unicode_whitespace_trans =dict .fromkeys (map (ord ,_whitespace ),ord (' '))
    word_punct =r'[\w!"\'&.,?]'
    letter =r'[^\d\W]'
    whitespace =r'[%s]'%re .escape (_whitespace )
    nowhitespace ='[^'+whitespace [1 :]
    wordsep_re =re .compile (r'''
        ( # any whitespace
          %(ws)s+
        | # em-dash between words
          (?<=%(wp)s) -{2,} (?=\w)
        | # word, possibly hyphenated
          %(nws)s+? (?:
            # hyphenated word
              -(?: (?<=%(lt)s{2}-) | (?<=%(lt)s-%(lt)s-))
              (?= %(lt)s -? %(lt)s)
            | # end of word
              (?=%(ws)s|\Z)
            | # em-dash
              (?<=%(wp)s) (?=-{2,}\w)
            )
        )'''%{'wp':word_punct ,'lt':letter ,
    "":whitespace ,'nws':nowhitespace },
    re .VERBOSE )
    del word_punct ,letter ,nowhitespace
    wordsep_simple_re =re .compile (r'(%s+)'%whitespace )
    del whitespace
    sentence_end_re =re .compile (r'[a-z]'
    "")
    def __init__ (self ,
    width =70 ,
    initial_indent ="",
    subsequent_indent ="",
    expand_tabs =True ,
    replace_whitespace =True ,
    fix_sentence_endings =False ,
    break_long_words =True ,
    drop_whitespace =True ,
    break_on_hyphens =True ,
    tabsize =8 ,
    *,
    max_lines =None ,
    placeholder =' [...]'):
        self .width =width
        self .initial_indent =initial_indent
        self .subsequent_indent =subsequent_indent
        self .expand_tabs =expand_tabs
        self .replace_whitespace =replace_whitespace
        self .fix_sentence_endings =fix_sentence_endings
        self .break_long_words =break_long_words
        self .drop_whitespace =drop_whitespace
        self .break_on_hyphens =break_on_hyphens
        self .tabsize =tabsize
        self .max_lines =max_lines
        self .placeholder =placeholder
    def _munge_whitespace (self ,text ):
        if self .expand_tabs :
            text =text .expandtabs (self .tabsize )
        if self .replace_whitespace :
            text =text .translate (self .unicode_whitespace_trans )
        return text
    def _split (self ,text ):
        if self .break_on_hyphens is True :
            chunks =self .wordsep_re .split (text )
        else :
            chunks =self .wordsep_simple_re .split (text )
        chunks =[c for c in chunks if c ]
        return chunks
    def _fix_sentence_endings (self ,chunks ):
        i =0
        patsearch =self .sentence_end_re .search
        while i <len (chunks )-1 :
            if chunks [i +1 ]==" "and patsearch (chunks [i ]):
                chunks [i +1 ]="  "
                i +=2
            else :
                i +=1
    def _handle_long_word (self ,reversed_chunks ,cur_line ,cur_len ,width ):
        if width <1 :
            space_left =1
        else :
            space_left =width -cur_len
        if self .break_long_words and space_left >0 :
            end =space_left
            chunk =reversed_chunks [-1 ]
            if self .break_on_hyphens and len (chunk )>space_left :
                hyphen =chunk .rfind ('-',0 ,space_left )
                if hyphen >0 and any (c !='-'for c in chunk [:hyphen ]):
                    end =hyphen +1
            cur_line .append (chunk [:end ])
            reversed_chunks [-1 ]=chunk [end :]
        elif not cur_line :
            cur_line .append (reversed_chunks .pop ())
    def _wrap_chunks (self ,chunks ):
        lines =[]
        if self .width <=0 :
            raise ValueError ("invalid width %r (must be > 0)"%self .width )
        if self .max_lines is not None :
            if self .max_lines >1 :
                indent =self .subsequent_indent
            else :
                indent =self .initial_indent
            if len (indent )+len (self .placeholder .lstrip ())>self .width :
                raise ValueError ("placeholder too large for max width")
        chunks .reverse ()
        while chunks :
            cur_line =[]
            cur_len =0
            if lines :
                indent =self .subsequent_indent
            else :
                indent =self .initial_indent
            width =self .width -len (indent )
            if self .drop_whitespace and chunks [-1 ].strip ()==''and lines :
                del chunks [-1 ]
            while chunks :
                l =len (chunks [-1 ])
                if cur_len +l <=width :
                    cur_line .append (chunks .pop ())
                    cur_len +=l
                else :
                    break
            if chunks and len (chunks [-1 ])>width :
                self ._handle_long_word (chunks ,cur_line ,cur_len ,width )
                cur_len =sum (map (len ,cur_line ))
            if self .drop_whitespace and cur_line and cur_line [-1 ].strip ()=='':
                cur_len -=len (cur_line [-1 ])
                del cur_line [-1 ]
            if cur_line :
                if (self .max_lines is None or
                len (lines )+1 <self .max_lines or
                (not chunks or
                self .drop_whitespace and
                len (chunks )==1 and
                not chunks [0 ].strip ())and cur_len <=width ):
                    lines .append (indent +''.join (cur_line ))
                else :
                    while cur_line :
                        if (cur_line [-1 ].strip ()and
                        cur_len +len (self .placeholder )<=width ):
                            cur_line .append (self .placeholder )
                            lines .append (indent +''.join (cur_line ))
                            break
                        cur_len -=len (cur_line [-1 ])
                        del cur_line [-1 ]
                    else :
                        if lines :
                            prev_line =lines [-1 ].rstrip ()
                            if (len (prev_line )+len (self .placeholder )<=
                            self .width ):
                                lines [-1 ]=prev_line +self .placeholder
                                break
                        lines .append (indent +self .placeholder .lstrip ())
                    break
        return lines
    def _split_chunks (self ,text ):
        text =self ._munge_whitespace (text )
        return self ._split (text )
    def wrap (self ,text ):
        chunks =self ._split_chunks (text )
        if self .fix_sentence_endings :
            self ._fix_sentence_endings (chunks )
        return self ._wrap_chunks (chunks )
    def fill (self ,text ):
        return "\n".join (self .wrap (text ))
def wrap (text ,width =70 ,**kwargs ):
    w =TextWrapper (width =width ,**kwargs )
    return w .wrap (text )
def fill (text ,width =70 ,**kwargs ):
    w =TextWrapper (width =width ,**kwargs )
    return w .fill (text )
def shorten (text ,width ,**kwargs ):
    w =TextWrapper (width =width ,max_lines =1 ,**kwargs )
    return w .fill (' '.join (text .strip ().split ()))
_whitespace_only_re =re .compile ('^[ \t]+$',re .MULTILINE )
_leading_whitespace_re =re .compile ('(^[ \t]*)(?:[^ \t\n])',re .MULTILINE )
def dedent (text ):
    margin =None
    text =_whitespace_only_re .sub ('',text )
    indents =_leading_whitespace_re .findall (text )
    for indent in indents :
        if margin is None :
            margin =indent
        elif indent .startswith (margin ):
            pass
        elif margin .startswith (indent ):
            margin =indent
        else :
            for i ,(x ,y )in enumerate (zip (margin ,indent )):
                if x !=y :
                    margin =margin [:i ]
                    break
    if 0 and margin :
        for line in text .split ("\n"):
            assert not line or line .startswith (margin ),"line = %r, margin = %r"%(line ,margin )
    if margin :
        text =re .sub (r'(?m)^'+margin ,'',text )
    return text
def indent (text ,prefix ,predicate =None ):
    if predicate is None :
        predicate =lambda s :not s .isspace ()
    prefixed_lines =[]
    for line in text .splitlines (True ):
        if predicate (line ):
            prefixed_lines .append (prefix )
        prefixed_lines .append (line )
    return ''.join (prefixed_lines )
if __name__ =="__main__":
    print (dedent ("Hello there.\n  This is indented."))
from math import log as _log ,exp as _exp ,pi as _pi ,e as _e ,ceil as _ceil
from math import sqrt as _sqrt ,acos as _acos ,cos as _cos ,sin as _sin
from math import tau as TWOPI ,floor as _floor ,isfinite as _isfinite
from math import lgamma as _lgamma ,fabs as _fabs ,log2 as _log2
from os import urandom as _urandom
from _collections_abc import Sequence as _Sequence
from operator import index as _index
from itertools import accumulate as _accumulate ,repeat as _repeat
from bisect import bisect as _bisect
import os as _os
import _random
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
"",
"",
"",
"",
]
NV_MAGICCONST =4 *_exp (-0.5 )/_sqrt (2.0 )
LOG4 =_log (4.0 )
SG_MAGICCONST =1.0 +_log (4.5 )
BPF =53
RECIP_BPF =2 **-BPF
_ONE =1
_sha512 =None
class Random (_random .Random ):
    VERSION =3
    def __init__ (self ,x =None ):
        self .seed (x )
        self .gauss_next =None
    def seed (self ,a =None ,version =2 ):
        if version ==1 and isinstance (a ,(str ,bytes )):
            a =a .decode ('latin-1')if isinstance (a ,bytes )else a
            x =ord (a [0 ])<<7 if a else 0
            for c in map (ord ,a ):
                x =((1000003 *x )^c )&0xFFFFFFFFFFFFFFFF
            x ^=len (a )
            a =-2 if x ==-1 else x
        elif version ==2 and isinstance (a ,(str ,bytes ,bytearray )):
            global _sha512
            if _sha512 is None :
                try :
                    from _sha2 import sha512 as _sha512
                except ImportError :
                    from hashlib import sha512 as _sha512
            if isinstance (a ,str ):
                a =a .encode ()
            a =int .from_bytes (a +_sha512 (a ).digest ())
        elif not isinstance (a ,(type (None ),int ,float ,str ,bytes ,bytearray )):
            raise TypeError ('The only supported seed types are:\n'
            "")
        super ().seed (a )
        self .gauss_next =None
    def getstate (self ):
        return self .VERSION ,super ().getstate (),self .gauss_next
    def setstate (self ,state ):
        version =state [0 ]
        if version ==3 :
            version ,internalstate ,self .gauss_next =state
            super ().setstate (internalstate )
        elif version ==2 :
            version ,internalstate ,self .gauss_next =state
            try :
                internalstate =tuple (x %(2 **32 )for x in internalstate )
            except ValueError as e :
                raise TypeError from e
            super ().setstate (internalstate )
        else :
            raise ValueError ("state with version %s passed to "
            ""%
            (version ,self .VERSION ))
    def __getstate__ (self ):
        return self .getstate ()
    def __setstate__ (self ,state ):
        self .setstate (state )
    def __reduce__ (self ):
        return self .__class__ ,(),self .getstate ()
    def __init_subclass__ (cls ,/,**kwargs ):
        for c in cls .__mro__ :
            if '_randbelow'in c .__dict__ :
                break
            if 'getrandbits'in c .__dict__ :
                cls ._randbelow =cls ._randbelow_with_getrandbits
                break
            if 'random'in c .__dict__ :
                cls ._randbelow =cls ._randbelow_without_getrandbits
                break
    def _randbelow_with_getrandbits (self ,n ):
        getrandbits =self .getrandbits
        k =n .bit_length ()
        r =getrandbits (k )
        while r >=n :
            r =getrandbits (k )
        return r
    def _randbelow_without_getrandbits (self ,n ,maxsize =1 <<BPF ):
        random =self .random
        if n >=maxsize :
            from warnings import warn
            warn ("Underlying random() generator does not supply \n"
            "")
            return _floor (random ()*n )
        rem =maxsize %n
        limit =(maxsize -rem )/maxsize
        r =random ()
        while r >=limit :
            r =random ()
        return _floor (r *maxsize )%n
    _randbelow =_randbelow_with_getrandbits
    def randbytes (self ,n ):
        return self .getrandbits (n *8 ).to_bytes (n ,'little')
    def randrange (self ,start ,stop =None ,step =_ONE ):
        istart =_index (start )
        if stop is None :
            if step is not _ONE :
                raise TypeError ("Missing a non-None stop argument")
            if istart >0 :
                return self ._randbelow (istart )
            raise ValueError ("empty range for randrange()")
        istop =_index (stop )
        width =istop -istart
        istep =_index (step )
        if istep ==1 :
            if width >0 :
                return istart +self ._randbelow (width )
            raise ValueError (f"empty range in randrange({start }, {stop })")
        if istep >0 :
            n =(width +istep -1 )//istep
        elif istep <0 :
            n =(width +istep +1 )//istep
        else :
            raise ValueError ("zero step for randrange()")
        if n <=0 :
            raise ValueError (f"empty range in randrange({start }, {stop }, {step })")
        return istart +istep *self ._randbelow (n )
    def randint (self ,a ,b ):
        return self .randrange (a ,b +1 )
    def choice (self ,seq ):
        if not len (seq ):
            raise IndexError ('Cannot choose from an empty sequence')
        return seq [self ._randbelow (len (seq ))]
    def shuffle (self ,x ):
        randbelow =self ._randbelow
        for i in reversed (range (1 ,len (x ))):
            j =randbelow (i +1 )
            x [i ],x [j ]=x [j ],x [i ]
    def sample (self ,population ,k ,*,counts =None ):
        if not isinstance (population ,_Sequence ):
            raise TypeError ("Population must be a sequence.  "
            "")
        n =len (population )
        if counts is not None :
            cum_counts =list (_accumulate (counts ))
            if len (cum_counts )!=n :
                raise ValueError ('The number of counts does not match the population')
            total =cum_counts .pop ()if cum_counts else 0
            if not isinstance (total ,int ):
                raise TypeError ('Counts must be integers')
            if total <0 :
                raise ValueError ('Counts must be non-negative')
            selections =self .sample (range (total ),k =k )
            bisect =_bisect
            return [population [bisect (cum_counts ,s )]for s in selections ]
        randbelow =self ._randbelow
        if not 0 <=k <=n :
            raise ValueError ("Sample larger than population or is negative")
        result =[None ]*k
        setsize =21
        if k >5 :
            setsize +=4 **_ceil (_log (k *3 ,4 ))
        if n <=setsize :
            pool =list (population )
            for i in range (k ):
                j =randbelow (n -i )
                result [i ]=pool [j ]
                pool [j ]=pool [n -i -1 ]
        else :
            selected =set ()
            selected_add =selected .add
            for i in range (k ):
                j =randbelow (n )
                while j in selected :
                    j =randbelow (n )
                selected_add (j )
                result [i ]=population [j ]
        return result
    def choices (self ,population ,weights =None ,*,cum_weights =None ,k =1 ):
        random =self .random
        n =len (population )
        if cum_weights is None :
            if weights is None :
                floor =_floor
                n +=0.0
                return [population [floor (random ()*n )]for i in _repeat (None ,k )]
            try :
                cum_weights =list (_accumulate (weights ))
            except TypeError :
                if not isinstance (weights ,int ):
                    raise
                k =weights
                raise TypeError (
                f'The number of choices must be a keyword argument: {k =}'
                )from None
        elif weights is not None :
            raise TypeError ('Cannot specify both weights and cumulative weights')
        if len (cum_weights )!=n :
            raise ValueError ('The number of weights does not match the population')
        total =cum_weights [-1 ]+0.0
        if total <=0.0 :
            raise ValueError ('Total of weights must be greater than zero')
        if not _isfinite (total ):
            raise ValueError ('Total of weights must be finite')
        bisect =_bisect
        hi =n -1
        return [population [bisect (cum_weights ,random ()*total ,0 ,hi )]
        for i in _repeat (None ,k )]
    def uniform (self ,a ,b ):
        return a +(b -a )*self .random ()
    def triangular (self ,low =0.0 ,high =1.0 ,mode =None ):
        u =self .random ()
        try :
            c =0.5 if mode is None else (mode -low )/(high -low )
        except ZeroDivisionError :
            return low
        if u >c :
            u =1.0 -u
            c =1.0 -c
            low ,high =high ,low
        return low +(high -low )*_sqrt (u *c )
    def normalvariate (self ,mu =0.0 ,sigma =1.0 ):
        random =self .random
        while True :
            u1 =random ()
            u2 =1.0 -random ()
            z =NV_MAGICCONST *(u1 -0.5 )/u2
            zz =z *z /4.0
            if zz <=-_log (u2 ):
                break
        return mu +z *sigma
    def gauss (self ,mu =0.0 ,sigma =1.0 ):
        random =self .random
        z =self .gauss_next
        self .gauss_next =None
        if z is None :
            x2pi =random ()*TWOPI
            g2rad =_sqrt (-2.0 *_log (1.0 -random ()))
            z =_cos (x2pi )*g2rad
            self .gauss_next =_sin (x2pi )*g2rad
        return mu +z *sigma
    def lognormvariate (self ,mu ,sigma ):
        return _exp (self .normalvariate (mu ,sigma ))
    def expovariate (self ,lambd =1.0 ):
        return -_log (1.0 -self .random ())/lambd
    def vonmisesvariate (self ,mu ,kappa ):
        random =self .random
        if kappa <=1e-6 :
            return TWOPI *random ()
        s =0.5 /kappa
        r =s +_sqrt (1.0 +s *s )
        while True :
            u1 =random ()
            z =_cos (_pi *u1 )
            d =z /(r +z )
            u2 =random ()
            if u2 <1.0 -d *d or u2 <=(1.0 -d )*_exp (d ):
                break
        q =1.0 /r
        f =(q +z )/(1.0 +q *z )
        u3 =random ()
        if u3 >0.5 :
            theta =(mu +_acos (f ))%TWOPI
        else :
            theta =(mu -_acos (f ))%TWOPI
        return theta
    def gammavariate (self ,alpha ,beta ):
        if alpha <=0.0 or beta <=0.0 :
            raise ValueError ('gammavariate: alpha and beta must be > 0.0')
        random =self .random
        if alpha >1.0 :
            ainv =_sqrt (2.0 *alpha -1.0 )
            bbb =alpha -LOG4
            ccc =alpha +ainv
            while True :
                u1 =random ()
                if not 1e-7 <u1 <0.9999999 :
                    continue
                u2 =1.0 -random ()
                v =_log (u1 /(1.0 -u1 ))/ainv
                x =alpha *_exp (v )
                z =u1 *u1 *u2
                r =bbb +ccc *v -x
                if r +SG_MAGICCONST -4.5 *z >=0.0 or r >=_log (z ):
                    return x *beta
        elif alpha ==1.0 :
            return -_log (1.0 -random ())*beta
        else :
            while True :
                u =random ()
                b =(_e +alpha )/_e
                p =b *u
                if p <=1.0 :
                    x =p **(1.0 /alpha )
                else :
                    x =-_log ((b -p )/alpha )
                u1 =random ()
                if p >1.0 :
                    if u1 <=x **(alpha -1.0 ):
                        break
                elif u1 <=_exp (-x ):
                    break
            return x *beta
    def betavariate (self ,alpha ,beta ):
        y =self .gammavariate (alpha ,1.0 )
        if y :
            return y /(y +self .gammavariate (beta ,1.0 ))
        return 0.0
    def paretovariate (self ,alpha ):
        u =1.0 -self .random ()
        return u **(-1.0 /alpha )
    def weibullvariate (self ,alpha ,beta ):
        u =1.0 -self .random ()
        return alpha *(-_log (u ))**(1.0 /beta )
    def binomialvariate (self ,n =1 ,p =0.5 ):
        if n <0 :
            raise ValueError ("n must be non-negative")
        if p <=0.0 or p >=1.0 :
            if p ==0.0 :
                return 0
            if p ==1.0 :
                return n
            raise ValueError ("p must be in the range 0.0 <= p <= 1.0")
        random =self .random
        if n ==1 :
            return _index (random ()<p )
        if p >0.5 :
            return n -self .binomialvariate (n ,1.0 -p )
        if n *p <10.0 :
            x =y =0
            c =_log2 (1.0 -p )
            if not c :
                return x
            while True :
                try :
                    y +=_floor (_log2 (random ())/c )+1
                except ValueError :
                    continue
                if y >n :
                    return x
                x +=1
        assert n *p >=10.0 and p <=0.5
        setup_complete =False
        spq =_sqrt (n *p *(1.0 -p ))
        b =1.15 +2.53 *spq
        a =-0.0873 +0.0248 *b +0.01 *p
        c =n *p +0.5
        vr =0.92 -4.2 /b
        while True :
            u =random ()
            u -=0.5
            us =0.5 -_fabs (u )
            try :
                k =_floor ((2.0 *a /us +b )*u +c )
            except ZeroDivisionError :
                continue
            if k <0 or k >n :
                continue
            v =random ()
            if us >=0.07 and v <=vr :
                return k
            if not setup_complete :
                alpha =(2.83 +5.1 /b )*spq
                lpq =_log (p /(1.0 -p ))
                m =_floor ((n +1 )*p )
                h =_lgamma (m +1 )+_lgamma (n -m +1 )
                setup_complete =True
            v *=alpha /(a /(us *us )+b )
            if _log (v )<=h -_lgamma (k +1 )-_lgamma (n -k +1 )+(k -m )*lpq :
                return k
class SystemRandom (Random ):
    def random (self ):
        return (int .from_bytes (_urandom (7 ))>>3 )*RECIP_BPF
    def getrandbits (self ,k ):
        if k <0 :
            raise ValueError ('number of bits must be non-negative')
        numbytes =(k +7 )//8
        x =int .from_bytes (_urandom (numbytes ))
        return x >>(numbytes *8 -k )
    def randbytes (self ,n ):
        return _urandom (n )
    def seed (self ,*args ,**kwds ):
        return None
    def _notimplemented (self ,*args ,**kwds ):
        raise NotImplementedError ('System entropy source does not have state.')
    getstate =setstate =_notimplemented
_inst =Random ()
seed =_inst .seed
random =_inst .random
uniform =_inst .uniform
triangular =_inst .triangular
randint =_inst .randint
choice =_inst .choice
randrange =_inst .randrange
sample =_inst .sample
shuffle =_inst .shuffle
choices =_inst .choices
normalvariate =_inst .normalvariate
lognormvariate =_inst .lognormvariate
expovariate =_inst .expovariate
vonmisesvariate =_inst .vonmisesvariate
gammavariate =_inst .gammavariate
gauss =_inst .gauss
betavariate =_inst .betavariate
binomialvariate =_inst .binomialvariate
paretovariate =_inst .paretovariate
weibullvariate =_inst .weibullvariate
getstate =_inst .getstate
setstate =_inst .setstate
getrandbits =_inst .getrandbits
randbytes =_inst .randbytes
def _test_generator (n ,func ,args ):
    from statistics import stdev ,fmean as mean
    from time import perf_counter
    t0 =perf_counter ()
    data =[func (*args )for i in _repeat (None ,n )]
    t1 =perf_counter ()
    xbar =mean (data )
    sigma =stdev (data ,xbar )
    low =min (data )
    high =max (data )
    print (f'{t1 -t0 :.3f} sec, {n } times {func .__name__ }{args !r }')
    print ('avg %g, stddev %g, min %g, max %g\n'%(xbar ,sigma ,low ,high ))
def _test (N =10_000 ):
    _test_generator (N ,random ,())
    _test_generator (N ,normalvariate ,(0.0 ,1.0 ))
    _test_generator (N ,lognormvariate ,(0.0 ,1.0 ))
    _test_generator (N ,vonmisesvariate ,(0.0 ,1.0 ))
    _test_generator (N ,binomialvariate ,(15 ,0.60 ))
    _test_generator (N ,binomialvariate ,(100 ,0.75 ))
    _test_generator (N ,gammavariate ,(0.01 ,1.0 ))
    _test_generator (N ,gammavariate ,(0.1 ,1.0 ))
    _test_generator (N ,gammavariate ,(0.1 ,2.0 ))
    _test_generator (N ,gammavariate ,(0.5 ,1.0 ))
    _test_generator (N ,gammavariate ,(0.9 ,1.0 ))
    _test_generator (N ,gammavariate ,(1.0 ,1.0 ))
    _test_generator (N ,gammavariate ,(2.0 ,1.0 ))
    _test_generator (N ,gammavariate ,(20.0 ,1.0 ))
    _test_generator (N ,gammavariate ,(200.0 ,1.0 ))
    _test_generator (N ,gauss ,(0.0 ,1.0 ))
    _test_generator (N ,betavariate ,(3.0 ,3.0 ))
    _test_generator (N ,triangular ,(0.0 ,1.0 ,1.0 /3.0 ))
if hasattr (_os ,"fork"):
    _os .register_at_fork (after_in_child =_inst .seed )
def _parse_args (arg_list :list [str ]|None ):
    import argparse
    parser =argparse .ArgumentParser (
    formatter_class =argparse .RawTextHelpFormatter )
    group =parser .add_mutually_exclusive_group ()
    group .add_argument (
    "","--choice",nargs ="+",
    help ="print a random choice")
    group .add_argument (
    "","--integer",type =int ,metavar ="N",
    help ="print a random integer between 1 and N inclusive")
    group .add_argument (
    "","--float",type =float ,metavar ="N",
    help ="print a random floating-point number between 0 and N inclusive")
    group .add_argument (
    "",type =int ,const =10_000 ,nargs ="?",
    help =argparse .SUPPRESS )
    parser .add_argument ("input",nargs ="*",
    help ="""\
if no options given, output depends on the input
    string or multiple: same as --choice
    integer: same as --integer
    float: same as --float""")
    args =parser .parse_args (arg_list )
    return args ,parser .format_help ()
def main (arg_list :list [str ]|None =None )->int |str :
    args ,help_text =_parse_args (arg_list )
    if args .choice :
        return choice (args .choice )
    if args .integer is not None :
        return randint (1 ,args .integer )
    if args .float is not None :
        return uniform (0 ,args .float )
    if args .test :
        _test (args .test )
        return ""
    if len (args .input )==1 :
        val =args .input [0 ]
        try :
            val =int (val )
            return randint (1 ,val )
        except ValueError :
            try :
                val =float (val )
                return uniform (0 ,val )
            except ValueError :
                return choice (val .split ())
    if len (args .input )>=2 :
        return choice (args .input )
    return help_text
if __name__ =='__main__':
    print (main ())
__all__ =["iskeyword","issoftkeyword","kwlist","softkwlist"]
kwlist =[
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
softkwlist =[
"",
"",
"",
]
iskeyword =frozenset (kwlist ).__contains__
issoftkeyword =frozenset (softkwlist ).__contains__
from decimal import Decimal
import functools
import math
import numbers
import operator
import re
import sys
__all__ =['Fraction']
_PyHASH_MODULUS =sys .hash_info .modulus
_PyHASH_INF =sys .hash_info .inf
@functools .lru_cache (maxsize =1 <<14 )
def _hash_algorithm (numerator ,denominator ):
    try :
        dinv =pow (denominator ,-1 ,_PyHASH_MODULUS )
    except ValueError :
        hash_ =_PyHASH_INF
    else :
        hash_ =hash (hash (abs (numerator ))*dinv )
    result =hash_ if numerator >=0 else -hash_
    return -2 if result ==-1 else result
_RATIONAL_FORMAT =re .compile (r"""
    \A\s*                                  # optional whitespace at the start,
    (?P<sign>[-+]?)                        # an optional sign, then
    (?=\d|\.\d)                            # lookahead for digit or .digit
    (?P<num>\d*|\d+(_\d+)*)                # numerator (possibly empty)
    (?:                                    # followed by
       (?:\s*/\s*(?P<denom>\d+(_\d+)*))?   # an optional denominator
    |                                      # or
       (?:\.(?P<decimal>\d*|\d+(_\d+)*))?  # an optional fractional part
       (?:E(?P<exp>[-+]?\d+(_\d+)*))?      # and optional exponent
    )
    \s*\Z                                  # and optional whitespace to finish
""",re .VERBOSE |re .IGNORECASE )
def _round_to_exponent (n ,d ,exponent ,no_neg_zero =False ):
    if exponent >=0 :
        d *=10 **exponent
    else :
        n *=10 **-exponent
    q ,r =divmod (n +(d >>1 ),d )
    if r ==0 and d &1 ==0 :
        q &=-2
    sign =q <0 if no_neg_zero else n <0
    return sign ,abs (q )
def _round_to_figures (n ,d ,figures ):
    if n ==0 :
        return False ,0 ,1 -figures
    str_n ,str_d =str (abs (n )),str (d )
    m =len (str_n )-len (str_d )+(str_d <=str_n )
    exponent =m -figures
    sign ,significand =_round_to_exponent (n ,d ,exponent )
    if len (str (significand ))==figures +1 :
        significand //=10
        exponent +=1
    return sign ,significand ,exponent
_GENERAL_FORMAT_SPECIFICATION_MATCHER =re .compile (r"""
    (?:
        (?P<fill>.)?
        (?P<align>[<>=^])
    )?
    (?P<sign>[-+ ]?)
    # Alt flag forces a slash and denominator in the output, even for
    # integer-valued Fraction objects.
    (?P<alt>\#)?
    # We don't implement the zeropad flag since there's no single obvious way
    # to interpret it.
    (?P<minimumwidth>0|[1-9][0-9]*)?
    (?P<thousands_sep>[,_])?
""",re .DOTALL |re .VERBOSE ).fullmatch
_FLOAT_FORMAT_SPECIFICATION_MATCHER =re .compile (r"""
    (?:
        (?P<fill>.)?
        (?P<align>[<>=^])
    )?
    (?P<sign>[-+ ]?)
    (?P<no_neg_zero>z)?
    (?P<alt>\#)?
    # A '0' that's *not* followed by another digit is parsed as a minimum width
    # rather than a zeropad flag.
    (?P<zeropad>0(?=[0-9]))?
    (?P<minimumwidth>0|[1-9][0-9]*)?
    (?P<thousands_sep>[,_])?
    (?:\.(?P<precision>0|[1-9][0-9]*))?
    (?P<presentation_type>[eEfFgG%])
""",re .DOTALL |re .VERBOSE ).fullmatch
class Fraction (numbers .Rational ):
    __slots__ =('_numerator','_denominator')
    def __new__ (cls ,numerator =0 ,denominator =None ):
        self =super (Fraction ,cls ).__new__ (cls )
        if denominator is None :
            if type (numerator )is int :
                self ._numerator =numerator
                self ._denominator =1
                return self
            elif isinstance (numerator ,numbers .Rational ):
                self ._numerator =numerator .numerator
                self ._denominator =numerator .denominator
                return self
            elif isinstance (numerator ,(float ,Decimal )):
                self ._numerator ,self ._denominator =numerator .as_integer_ratio ()
                return self
            elif isinstance (numerator ,str ):
                m =_RATIONAL_FORMAT .match (numerator )
                if m is None :
                    raise ValueError ('Invalid literal for Fraction: %r'%
                    numerator )
                numerator =int (m .group ('num')or '0')
                denom =m .group ('denom')
                if denom :
                    denominator =int (denom )
                else :
                    denominator =1
                    decimal =m .group ('decimal')
                    if decimal :
                        decimal =decimal .replace ('_','')
                        scale =10 **len (decimal )
                        numerator =numerator *scale +int (decimal )
                        denominator *=scale
                    exp =m .group ('exp')
                    if exp :
                        exp =int (exp )
                        if exp >=0 :
                            numerator *=10 **exp
                        else :
                            denominator *=10 **-exp
                if m .group ('sign')=='-':
                    numerator =-numerator
            else :
                raise TypeError ("argument should be a string "
                "")
        elif type (numerator )is int is type (denominator ):
            pass
        elif (isinstance (numerator ,numbers .Rational )and
        isinstance (denominator ,numbers .Rational )):
            numerator ,denominator =(
            numerator .numerator *denominator .denominator ,
            denominator .numerator *numerator .denominator
            )
        else :
            raise TypeError ("both arguments should be "
            "")
        if denominator ==0 :
            raise ZeroDivisionError ('Fraction(%s, 0)'%numerator )
        g =math .gcd (numerator ,denominator )
        if denominator <0 :
            g =-g
        numerator //=g
        denominator //=g
        self ._numerator =numerator
        self ._denominator =denominator
        return self
    @classmethod
    def from_float (cls ,f ):
        if isinstance (f ,numbers .Integral ):
            return cls (f )
        elif not isinstance (f ,float ):
            raise TypeError ("%s.from_float() only takes floats, not %r (%s)"%
            (cls .__name__ ,f ,type (f ).__name__ ))
        return cls ._from_coprime_ints (*f .as_integer_ratio ())
    @classmethod
    def from_decimal (cls ,dec ):
        from decimal import Decimal
        if isinstance (dec ,numbers .Integral ):
            dec =Decimal (int (dec ))
        elif not isinstance (dec ,Decimal ):
            raise TypeError (
            ""%
            (cls .__name__ ,dec ,type (dec ).__name__ ))
        return cls ._from_coprime_ints (*dec .as_integer_ratio ())
    @classmethod
    def _from_coprime_ints (cls ,numerator ,denominator ,/):
        obj =super (Fraction ,cls ).__new__ (cls )
        obj ._numerator =numerator
        obj ._denominator =denominator
        return obj
    def is_integer (self ):
        return self ._denominator ==1
    def as_integer_ratio (self ):
        return (self ._numerator ,self ._denominator )
    def limit_denominator (self ,max_denominator =1000000 ):
        if max_denominator <1 :
            raise ValueError ("max_denominator should be at least 1")
        if self ._denominator <=max_denominator :
            return Fraction (self )
        p0 ,q0 ,p1 ,q1 =0 ,1 ,1 ,0
        n ,d =self ._numerator ,self ._denominator
        while True :
            a =n //d
            q2 =q0 +a *q1
            if q2 >max_denominator :
                break
            p0 ,q0 ,p1 ,q1 =p1 ,q1 ,p0 +a *p1 ,q2
            n ,d =d ,n -a *d
        k =(max_denominator -q0 )//q1
        if 2 *d *(q0 +k *q1 )<=self ._denominator :
            return Fraction ._from_coprime_ints (p1 ,q1 )
        else :
            return Fraction ._from_coprime_ints (p0 +k *p1 ,q0 +k *q1 )
    @property
    def numerator (a ):
        return a ._numerator
    @property
    def denominator (a ):
        return a ._denominator
    def __repr__ (self ):
        return '%s(%s, %s)'%(self .__class__ .__name__ ,
        self ._numerator ,self ._denominator )
    def __str__ (self ):
        if self ._denominator ==1 :
            return str (self ._numerator )
        else :
            return '%s/%s'%(self ._numerator ,self ._denominator )
    def _format_general (self ,match ):
        fill =match ["fill"]or " "
        align =match ["align"]or ">"
        pos_sign =""if match ["sign"]=="-"else match ["sign"]
        alternate_form =bool (match ["alt"])
        minimumwidth =int (match ["minimumwidth"]or "0")
        thousands_sep =match ["thousands_sep"]or ''
        n ,d =self ._numerator ,self ._denominator
        if d >1 or alternate_form :
            body =f"{abs (n ):{thousands_sep }}/{d :{thousands_sep }}"
        else :
            body =f"{abs (n ):{thousands_sep }}"
        sign ='-'if n <0 else pos_sign
        padding =fill *(minimumwidth -len (sign )-len (body ))
        if align ==">":
            return padding +sign +body
        elif align =="<":
            return sign +body +padding
        elif align =="^":
            half =len (padding )//2
            return padding [:half ]+sign +body +padding [half :]
        else :
            return sign +padding +body
    def _format_float_style (self ,match ):
        fill =match ["fill"]or " "
        align =match ["align"]or ">"
        pos_sign =""if match ["sign"]=="-"else match ["sign"]
        no_neg_zero =bool (match ["no_neg_zero"])
        alternate_form =bool (match ["alt"])
        zeropad =bool (match ["zeropad"])
        minimumwidth =int (match ["minimumwidth"]or "0")
        thousands_sep =match ["thousands_sep"]
        precision =int (match ["precision"]or "6")
        presentation_type =match ["presentation_type"]
        trim_zeros =presentation_type in "gG"and not alternate_form
        trim_point =not alternate_form
        exponent_indicator ="E"if presentation_type in "EFG"else "e"
        if align =='='and fill =='0':
            zeropad =True
        if presentation_type in "fF%":
            exponent =-precision
            if presentation_type =="%":
                exponent -=2
            negative ,significand =_round_to_exponent (
            self ._numerator ,self ._denominator ,exponent ,no_neg_zero )
            scientific =False
            point_pos =precision
        else :
            figures =(
            max (precision ,1 )
            if presentation_type in "gG"
            else precision +1
            )
            negative ,significand ,exponent =_round_to_figures (
            self ._numerator ,self ._denominator ,figures )
            scientific =(
            presentation_type in "eE"
            or exponent >0
            or exponent +figures <=-4
            )
            point_pos =figures -1 if scientific else -exponent
        if presentation_type =="%":
            suffix ="%"
        elif scientific :
            suffix =f"{exponent_indicator }{exponent +point_pos :+03d}"
        else :
            suffix =""
        digits =f"{significand :0{point_pos +1 }d}"
        sign ="-"if negative else pos_sign
        leading =digits [:len (digits )-point_pos ]
        frac_part =digits [len (digits )-point_pos :]
        if trim_zeros :
            frac_part =frac_part .rstrip ("0")
        separator =""if trim_point and not frac_part else "."
        trailing =separator +frac_part +suffix
        if zeropad :
            min_leading =minimumwidth -len (sign )-len (trailing )
            leading =leading .zfill (
            3 *min_leading //4 +1 if thousands_sep else min_leading
            )
        if thousands_sep :
            first_pos =1 +(len (leading )-1 )%3
            leading =leading [:first_pos ]+"".join (
            thousands_sep +leading [pos :pos +3 ]
            for pos in range (first_pos ,len (leading ),3 )
            )
        body =leading +trailing
        padding =fill *(minimumwidth -len (sign )-len (body ))
        if align ==">":
            return padding +sign +body
        elif align =="<":
            return sign +body +padding
        elif align =="^":
            half =len (padding )//2
            return padding [:half ]+sign +body +padding [half :]
        else :
            return sign +padding +body
    def __format__ (self ,format_spec ,/):
        if match :=_GENERAL_FORMAT_SPECIFICATION_MATCHER (format_spec ):
            return self ._format_general (match )
        if match :=_FLOAT_FORMAT_SPECIFICATION_MATCHER (format_spec ):
            if match ["align"]is None or match ["zeropad"]is None :
                return self ._format_float_style (match )
        raise ValueError (
        f"Invalid format specifier {format_spec !r } "
        f"for object of type {type (self ).__name__ !r }"
        )
    def _operator_fallbacks (monomorphic_operator ,fallback_operator ,
    handle_complex =True ):
        def forward (a ,b ):
            if isinstance (b ,Fraction ):
                return monomorphic_operator (a ,b )
            elif isinstance (b ,int ):
                return monomorphic_operator (a ,Fraction (b ))
            elif isinstance (b ,float ):
                return fallback_operator (float (a ),b )
            elif handle_complex and isinstance (b ,complex ):
                return fallback_operator (complex (a ),b )
            else :
                return NotImplemented
        forward .__name__ ='__'+fallback_operator .__name__ +'__'
        forward .__doc__ =monomorphic_operator .__doc__
        def reverse (b ,a ):
            if isinstance (a ,numbers .Rational ):
                return monomorphic_operator (Fraction (a ),b )
            elif isinstance (a ,numbers .Real ):
                return fallback_operator (float (a ),float (b ))
            elif handle_complex and isinstance (a ,numbers .Complex ):
                return fallback_operator (complex (a ),complex (b ))
            else :
                return NotImplemented
        reverse .__name__ ='__r'+fallback_operator .__name__ +'__'
        reverse .__doc__ =monomorphic_operator .__doc__
        return forward ,reverse
    def _add (a ,b ):
        na ,da =a ._numerator ,a ._denominator
        nb ,db =b ._numerator ,b ._denominator
        g =math .gcd (da ,db )
        if g ==1 :
            return Fraction ._from_coprime_ints (na *db +da *nb ,da *db )
        s =da //g
        t =na *(db //g )+nb *s
        g2 =math .gcd (t ,g )
        if g2 ==1 :
            return Fraction ._from_coprime_ints (t ,s *db )
        return Fraction ._from_coprime_ints (t //g2 ,s *(db //g2 ))
    __add__ ,__radd__ =_operator_fallbacks (_add ,operator .add )
    def _sub (a ,b ):
        na ,da =a ._numerator ,a ._denominator
        nb ,db =b ._numerator ,b ._denominator
        g =math .gcd (da ,db )
        if g ==1 :
            return Fraction ._from_coprime_ints (na *db -da *nb ,da *db )
        s =da //g
        t =na *(db //g )-nb *s
        g2 =math .gcd (t ,g )
        if g2 ==1 :
            return Fraction ._from_coprime_ints (t ,s *db )
        return Fraction ._from_coprime_ints (t //g2 ,s *(db //g2 ))
    __sub__ ,__rsub__ =_operator_fallbacks (_sub ,operator .sub )
    def _mul (a ,b ):
        na ,da =a ._numerator ,a ._denominator
        nb ,db =b ._numerator ,b ._denominator
        g1 =math .gcd (na ,db )
        if g1 >1 :
            na //=g1
            db //=g1
        g2 =math .gcd (nb ,da )
        if g2 >1 :
            nb //=g2
            da //=g2
        return Fraction ._from_coprime_ints (na *nb ,db *da )
    __mul__ ,__rmul__ =_operator_fallbacks (_mul ,operator .mul )
    def _div (a ,b ):
        nb ,db =b ._numerator ,b ._denominator
        if nb ==0 :
            raise ZeroDivisionError ('Fraction(%s, 0)'%db )
        na ,da =a ._numerator ,a ._denominator
        g1 =math .gcd (na ,nb )
        if g1 >1 :
            na //=g1
            nb //=g1
        g2 =math .gcd (db ,da )
        if g2 >1 :
            da //=g2
            db //=g2
        n ,d =na *db ,nb *da
        if d <0 :
            n ,d =-n ,-d
        return Fraction ._from_coprime_ints (n ,d )
    __truediv__ ,__rtruediv__ =_operator_fallbacks (_div ,operator .truediv )
    def _floordiv (a ,b ):
        return (a .numerator *b .denominator )//(a .denominator *b .numerator )
    __floordiv__ ,__rfloordiv__ =_operator_fallbacks (_floordiv ,operator .floordiv ,False )
    def _divmod (a ,b ):
        da ,db =a .denominator ,b .denominator
        div ,n_mod =divmod (a .numerator *db ,da *b .numerator )
        return div ,Fraction (n_mod ,da *db )
    __divmod__ ,__rdivmod__ =_operator_fallbacks (_divmod ,divmod ,False )
    def _mod (a ,b ):
        da ,db =a .denominator ,b .denominator
        return Fraction ((a .numerator *db )%(b .numerator *da ),da *db )
    __mod__ ,__rmod__ =_operator_fallbacks (_mod ,operator .mod ,False )
    def __pow__ (a ,b ):
        if isinstance (b ,numbers .Rational ):
            if b .denominator ==1 :
                power =b .numerator
                if power >=0 :
                    return Fraction ._from_coprime_ints (a ._numerator **power ,
                    a ._denominator **power )
                elif a ._numerator >0 :
                    return Fraction ._from_coprime_ints (a ._denominator **-power ,
                    a ._numerator **-power )
                elif a ._numerator ==0 :
                    raise ZeroDivisionError ('Fraction(%s, 0)'%
                    a ._denominator **-power )
                else :
                    return Fraction ._from_coprime_ints ((-a ._denominator )**-power ,
                    (-a ._numerator )**-power )
            else :
                return float (a )**float (b )
        elif isinstance (b ,(float ,complex )):
            return float (a )**b
        else :
            return NotImplemented
    def __rpow__ (b ,a ):
        if b ._denominator ==1 and b ._numerator >=0 :
            return a **b ._numerator
        if isinstance (a ,numbers .Rational ):
            return Fraction (a .numerator ,a .denominator )**b
        if b ._denominator ==1 :
            return a **b ._numerator
        return a **float (b )
    def __pos__ (a ):
        return Fraction ._from_coprime_ints (a ._numerator ,a ._denominator )
    def __neg__ (a ):
        return Fraction ._from_coprime_ints (-a ._numerator ,a ._denominator )
    def __abs__ (a ):
        return Fraction ._from_coprime_ints (abs (a ._numerator ),a ._denominator )
    def __int__ (a ,_index =operator .index ):
        if a ._numerator <0 :
            return _index (-(-a ._numerator //a ._denominator ))
        else :
            return _index (a ._numerator //a ._denominator )
    def __trunc__ (a ):
        if a ._numerator <0 :
            return -(-a ._numerator //a ._denominator )
        else :
            return a ._numerator //a ._denominator
    def __floor__ (a ):
        return a ._numerator //a ._denominator
    def __ceil__ (a ):
        return -(-a ._numerator //a ._denominator )
    def __round__ (self ,ndigits =None ):
        if ndigits is None :
            d =self ._denominator
            floor ,remainder =divmod (self ._numerator ,d )
            if remainder *2 <d :
                return floor
            elif remainder *2 >d :
                return floor +1
            elif floor %2 ==0 :
                return floor
            else :
                return floor +1
        shift =10 **abs (ndigits )
        if ndigits >0 :
            return Fraction (round (self *shift ),shift )
        else :
            return Fraction (round (self /shift )*shift )
    def __hash__ (self ):
        return _hash_algorithm (self ._numerator ,self ._denominator )
    def __eq__ (a ,b ):
        if type (b )is int :
            return a ._numerator ==b and a ._denominator ==1
        if isinstance (b ,numbers .Rational ):
            return (a ._numerator ==b .numerator and
            a ._denominator ==b .denominator )
        if isinstance (b ,numbers .Complex )and b .imag ==0 :
            b =b .real
        if isinstance (b ,float ):
            if math .isnan (b )or math .isinf (b ):
                return 0.0 ==b
            else :
                return a ==a .from_float (b )
        else :
            return NotImplemented
    def _richcmp (self ,other ,op ):
        if isinstance (other ,numbers .Rational ):
            return op (self ._numerator *other .denominator ,
            self ._denominator *other .numerator )
        if isinstance (other ,float ):
            if math .isnan (other )or math .isinf (other ):
                return op (0.0 ,other )
            else :
                return op (self ,self .from_float (other ))
        else :
            return NotImplemented
    def __lt__ (a ,b ):
        return a ._richcmp (b ,operator .lt )
    def __gt__ (a ,b ):
        return a ._richcmp (b ,operator .gt )
    def __le__ (a ,b ):
        return a ._richcmp (b ,operator .le )
    def __ge__ (a ,b ):
        return a ._richcmp (b ,operator .ge )
    def __bool__ (a ):
        return bool (a ._numerator )
    def __reduce__ (self ):
        return (self .__class__ ,(self ._numerator ,self ._denominator ))
    def __copy__ (self ):
        if type (self )==Fraction :
            return self
        return self .__class__ (self ._numerator ,self ._denominator )
    def __deepcopy__ (self ,memo ):
        if type (self )==Fraction :
            return self
        return self .__class__ (self ._numerator ,self ._denominator )
__about__ ="""Heap queues
[explanation by François Pinard]
Heaps are arrays for which a[k] <= a[2*k+1] and a[k] <= a[2*k+2] for
all k, counting elements from 0.  For the sake of comparison,
non-existing elements are considered to be infinite.  The interesting
property of a heap is that a[0] is always its smallest element.
The strange invariant above is meant to be an efficient memory
representation for a tournament.  The numbers below are `k', not a[k]:
                                   0
                  1                                 2
          3               4                5               6
      7       8       9       10      11      12      13      14
    15 16   17 18   19 20   21 22   23 24   25 26   27 28   29 30
In the tree above, each cell `k' is topping `2*k+1' and `2*k+2'.  In
a usual binary tournament we see in sports, each cell is the winner
over the two cells it tops, and we can trace the winner down the tree
to see all opponents s/he had.  However, in many computer applications
of such tournaments, we do not need to trace the history of a winner.
To be more memory efficient, when a winner is promoted, we try to
replace it by something else at a lower level, and the rule becomes
that a cell and the two cells it tops contain three different items,
but the top cell "wins" over the two topped cells.
If this heap invariant is protected at all time, index 0 is clearly
the overall winner.  The simplest algorithmic way to remove it and
find the "next" winner is to move some loser (let's say cell 30 in the
diagram above) into the 0 position, and then percolate this new 0 down
the tree, exchanging values, until the invariant is re-established.
This is clearly logarithmic on the total number of items in the tree.
By iterating over all items, you get an O(n ln n) sort.
A nice feature of this sort is that you can efficiently insert new
items while the sort is going on, provided that the inserted items are
not "better" than the last 0'th element you extracted.  This is
especially useful in simulation contexts, where the tree holds all
incoming events, and the "win" condition means the smallest scheduled
time.  When an event schedule other events for execution, they are
scheduled into the future, so they can easily go into the heap.  So, a
heap is a good structure for implementing schedulers (this is what I
used for my MIDI sequencer :-).
Various structures for implementing schedulers have been extensively
studied, and heaps are good for this, as they are reasonably speedy,
the speed is almost constant, and the worst case is not much different
than the average case.  However, there are other representations which
are more efficient overall, yet the worst cases might be terrible.
Heaps are also very useful in big disk sorts.  You most probably all
know that a big sort implies producing "runs" (which are pre-sorted
sequences, which size is usually related to the amount of CPU memory),
followed by a merging passes for these runs, which merging is often
very cleverly organised[1].  It is very important that the initial
sort produces the longest runs possible.  Tournaments are a good way
to that.  If, using all the memory available to hold a tournament, you
replace and percolate items that happen to fit the current run, you'll
produce runs which are twice the size of the memory for random input,
and much better for input fuzzily ordered.
Moreover, if you output the 0'th item on disk and get an input which
may not fit in the current tournament (because the value "wins" over
the last output value), it cannot fit in the heap, so the size of the
heap decreases.  The freed memory could be cleverly reused immediately
for progressively building a second heap, which grows at exactly the
same rate the first heap is melting.  When the first heap completely
vanishes, you switch heaps and start a new run.  Clever and quite
effective!
In a word, heaps are useful memory structures to know.  I use them in
a few applications, and I think it is good to keep a `heap' module
around. :-)
--------------------
[1] The disk balancing algorithms which are current, nowadays, are
more annoying than clever, and this is a consequence of the seeking
capabilities of the disks.  On devices which cannot seek, like big
tape drives, the story was quite different, and one had to be very
clever to ensure (far in advance) that each tape movement will be the
most effective possible (that is, will best participate at
"progressing" the merge).  Some tapes were even able to read
backwards, and this was also used to avoid the rewinding time.
Believe me, real good tape sorts were quite spectacular to watch!
From all times, sorting has always been a Great Art! :-)
"""
__all__ =['heappush','heappop','heapify','heapreplace','merge',
"",'nsmallest','heappushpop']
def heappush (heap ,item ):
    heap .append (item )
    _siftdown (heap ,0 ,len (heap )-1 )
def heappop (heap ):
    lastelt =heap .pop ()
    if heap :
        returnitem =heap [0 ]
        heap [0 ]=lastelt
        _siftup (heap ,0 )
        return returnitem
    return lastelt
def heapreplace (heap ,item ):
    returnitem =heap [0 ]
    heap [0 ]=item
    _siftup (heap ,0 )
    return returnitem
def heappushpop (heap ,item ):
    if heap and heap [0 ]<item :
        item ,heap [0 ]=heap [0 ],item
        _siftup (heap ,0 )
    return item
def heapify (x ):
    n =len (x )
    for i in reversed (range (n //2 )):
        _siftup (x ,i )
def _heappop_max (heap ):
    lastelt =heap .pop ()
    if heap :
        returnitem =heap [0 ]
        heap [0 ]=lastelt
        _siftup_max (heap ,0 )
        return returnitem
    return lastelt
def _heapreplace_max (heap ,item ):
    returnitem =heap [0 ]
    heap [0 ]=item
    _siftup_max (heap ,0 )
    return returnitem
def _heapify_max (x ):
    n =len (x )
    for i in reversed (range (n //2 )):
        _siftup_max (x ,i )
def _siftdown (heap ,startpos ,pos ):
    newitem =heap [pos ]
    while pos >startpos :
        parentpos =(pos -1 )>>1
        parent =heap [parentpos ]
        if newitem <parent :
            heap [pos ]=parent
            pos =parentpos
            continue
        break
    heap [pos ]=newitem
def _siftup (heap ,pos ):
    endpos =len (heap )
    startpos =pos
    newitem =heap [pos ]
    childpos =2 *pos +1
    while childpos <endpos :
        rightpos =childpos +1
        if rightpos <endpos and not heap [childpos ]<heap [rightpos ]:
            childpos =rightpos
        heap [pos ]=heap [childpos ]
        pos =childpos
        childpos =2 *pos +1
    heap [pos ]=newitem
    _siftdown (heap ,startpos ,pos )
def _siftdown_max (heap ,startpos ,pos ):
    newitem =heap [pos ]
    while pos >startpos :
        parentpos =(pos -1 )>>1
        parent =heap [parentpos ]
        if parent <newitem :
            heap [pos ]=parent
            pos =parentpos
            continue
        break
    heap [pos ]=newitem
def _siftup_max (heap ,pos ):
    endpos =len (heap )
    startpos =pos
    newitem =heap [pos ]
    childpos =2 *pos +1
    while childpos <endpos :
        rightpos =childpos +1
        if rightpos <endpos and not heap [rightpos ]<heap [childpos ]:
            childpos =rightpos
        heap [pos ]=heap [childpos ]
        pos =childpos
        childpos =2 *pos +1
    heap [pos ]=newitem
    _siftdown_max (heap ,startpos ,pos )
def merge (*iterables ,key =None ,reverse =False ):
    h =[]
    h_append =h .append
    if reverse :
        _heapify =_heapify_max
        _heappop =_heappop_max
        _heapreplace =_heapreplace_max
        direction =-1
    else :
        _heapify =heapify
        _heappop =heappop
        _heapreplace =heapreplace
        direction =1
    if key is None :
        for order ,it in enumerate (map (iter ,iterables )):
            try :
                next =it .__next__
                h_append ([next (),order *direction ,next ])
            except StopIteration :
                pass
        _heapify (h )
        while len (h )>1 :
            try :
                while True :
                    value ,order ,next =s =h [0 ]
                    yield value
                    s [0 ]=next ()
                    _heapreplace (h ,s )
            except StopIteration :
                _heappop (h )
        if h :
            value ,order ,next =h [0 ]
            yield value
            yield from next .__self__
        return
    for order ,it in enumerate (map (iter ,iterables )):
        try :
            next =it .__next__
            value =next ()
            h_append ([key (value ),order *direction ,value ,next ])
        except StopIteration :
            pass
    _heapify (h )
    while len (h )>1 :
        try :
            while True :
                key_value ,order ,value ,next =s =h [0 ]
                yield value
                value =next ()
                s [0 ]=key (value )
                s [2 ]=value
                _heapreplace (h ,s )
        except StopIteration :
            _heappop (h )
    if h :
        key_value ,order ,value ,next =h [0 ]
        yield value
        yield from next .__self__
def nsmallest (n ,iterable ,key =None ):
    if n ==1 :
        it =iter (iterable )
        sentinel =object ()
        result =min (it ,default =sentinel ,key =key )
        return []if result is sentinel else [result ]
    try :
        size =len (iterable )
    except (TypeError ,AttributeError ):
        pass
    else :
        if n >=size :
            return sorted (iterable ,key =key )[:n ]
    if key is None :
        it =iter (iterable )
        result =[(elem ,i )for i ,elem in zip (range (n ),it )]
        if not result :
            return result
        _heapify_max (result )
        top =result [0 ][0 ]
        order =n
        _heapreplace =_heapreplace_max
        for elem in it :
            if elem <top :
                _heapreplace (result ,(elem ,order ))
                top ,_order =result [0 ]
                order +=1
        result .sort ()
        return [elem for (elem ,order )in result ]
    it =iter (iterable )
    result =[(key (elem ),i ,elem )for i ,elem in zip (range (n ),it )]
    if not result :
        return result
    _heapify_max (result )
    top =result [0 ][0 ]
    order =n
    _heapreplace =_heapreplace_max
    for elem in it :
        k =key (elem )
        if k <top :
            _heapreplace (result ,(k ,order ,elem ))
            top ,_order ,_elem =result [0 ]
            order +=1
    result .sort ()
    return [elem for (k ,order ,elem )in result ]
def nlargest (n ,iterable ,key =None ):
    if n ==1 :
        it =iter (iterable )
        sentinel =object ()
        result =max (it ,default =sentinel ,key =key )
        return []if result is sentinel else [result ]
    try :
        size =len (iterable )
    except (TypeError ,AttributeError ):
        pass
    else :
        if n >=size :
            return sorted (iterable ,key =key ,reverse =True )[:n ]
    if key is None :
        it =iter (iterable )
        result =[(elem ,i )for i ,elem in zip (range (0 ,-n ,-1 ),it )]
        if not result :
            return result
        heapify (result )
        top =result [0 ][0 ]
        order =-n
        _heapreplace =heapreplace
        for elem in it :
            if top <elem :
                _heapreplace (result ,(elem ,order ))
                top ,_order =result [0 ]
                order -=1
        result .sort (reverse =True )
        return [elem for (elem ,order )in result ]
    it =iter (iterable )
    result =[(key (elem ),i ,elem )for i ,elem in zip (range (0 ,-n ,-1 ),it )]
    if not result :
        return result
    heapify (result )
    top =result [0 ][0 ]
    order =-n
    _heapreplace =heapreplace
    for elem in it :
        k =key (elem )
        if top <k :
            _heapreplace (result ,(k ,order ,elem ))
            top ,_order ,_elem =result [0 ]
            order -=1
    result .sort (reverse =True )
    return [elem for (k ,order ,elem )in result ]
try :
    from _heapq import *
except ImportError :
    pass
try :
    from _heapq import _heapreplace_max
except ImportError :
    pass
try :
    from _heapq import _heapify_max
except ImportError :
    pass
try :
    from _heapq import _heappop_max
except ImportError :
    pass
if __name__ =="__main__":
    import doctest
    print (doctest .testmod ())
__all__ =['get_close_matches','ndiff','restore','SequenceMatcher',
"",'IS_CHARACTER_JUNK','IS_LINE_JUNK','context_diff',
"",'diff_bytes','HtmlDiff','Match']
from heapq import nlargest as _nlargest
from collections import namedtuple as _namedtuple
from types import GenericAlias
Match =_namedtuple ('Match','a b size')
def _calculate_ratio (matches ,length ):
    if length :
        return 2.0 *matches /length
    return 1.0
class SequenceMatcher :
    def __init__ (self ,isjunk =None ,a ='',b ='',autojunk =True ):
        self .isjunk =isjunk
        self .a =self .b =None
        self .autojunk =autojunk
        self .set_seqs (a ,b )
    def set_seqs (self ,a ,b ):
        self .set_seq1 (a )
        self .set_seq2 (b )
    def set_seq1 (self ,a ):
        if a is self .a :
            return
        self .a =a
        self .matching_blocks =self .opcodes =None
    def set_seq2 (self ,b ):
        if b is self .b :
            return
        self .b =b
        self .matching_blocks =self .opcodes =None
        self .fullbcount =None
        self .__chain_b ()
    def __chain_b (self ):
        b =self .b
        self .b2j =b2j ={}
        for i ,elt in enumerate (b ):
            indices =b2j .setdefault (elt ,[])
            indices .append (i )
        self .bjunk =junk =set ()
        isjunk =self .isjunk
        if isjunk :
            for elt in b2j .keys ():
                if isjunk (elt ):
                    junk .add (elt )
            for elt in junk :
                del b2j [elt ]
        self .bpopular =popular =set ()
        n =len (b )
        if self .autojunk and n >=200 :
            ntest =n //100 +1
            for elt ,idxs in b2j .items ():
                if len (idxs )>ntest :
                    popular .add (elt )
            for elt in popular :
                del b2j [elt ]
    def find_longest_match (self ,alo =0 ,ahi =None ,blo =0 ,bhi =None ):
        a ,b ,b2j ,isbjunk =self .a ,self .b ,self .b2j ,self .bjunk .__contains__
        if ahi is None :
            ahi =len (a )
        if bhi is None :
            bhi =len (b )
        besti ,bestj ,bestsize =alo ,blo ,0
        j2len ={}
        nothing =[]
        for i in range (alo ,ahi ):
            j2lenget =j2len .get
            newj2len ={}
            for j in b2j .get (a [i ],nothing ):
                if j <blo :
                    continue
                if j >=bhi :
                    break
                k =newj2len [j ]=j2lenget (j -1 ,0 )+1
                if k >bestsize :
                    besti ,bestj ,bestsize =i -k +1 ,j -k +1 ,k
            j2len =newj2len
        while besti >alo and bestj >blo and not isbjunk (b [bestj -1 ])and a [besti -1 ]==b [bestj -1 ]:
            besti ,bestj ,bestsize =besti -1 ,bestj -1 ,bestsize +1
        while besti +bestsize <ahi and bestj +bestsize <bhi and not isbjunk (b [bestj +bestsize ])and a [besti +bestsize ]==b [bestj +bestsize ]:
            bestsize +=1
        while besti >alo and bestj >blo and isbjunk (b [bestj -1 ])and a [besti -1 ]==b [bestj -1 ]:
            besti ,bestj ,bestsize =besti -1 ,bestj -1 ,bestsize +1
        while besti +bestsize <ahi and bestj +bestsize <bhi and isbjunk (b [bestj +bestsize ])and a [besti +bestsize ]==b [bestj +bestsize ]:
            bestsize =bestsize +1
        return Match (besti ,bestj ,bestsize )
    def get_matching_blocks (self ):
        if self .matching_blocks is not None :
            return self .matching_blocks
        la ,lb =len (self .a ),len (self .b )
        queue =[(0 ,la ,0 ,lb )]
        matching_blocks =[]
        while queue :
            alo ,ahi ,blo ,bhi =queue .pop ()
            i ,j ,k =x =self .find_longest_match (alo ,ahi ,blo ,bhi )
            if k :
                matching_blocks .append (x )
                if alo <i and blo <j :
                    queue .append ((alo ,i ,blo ,j ))
                if i +k <ahi and j +k <bhi :
                    queue .append ((i +k ,ahi ,j +k ,bhi ))
        matching_blocks .sort ()
        i1 =j1 =k1 =0
        non_adjacent =[]
        for i2 ,j2 ,k2 in matching_blocks :
            if i1 +k1 ==i2 and j1 +k1 ==j2 :
                k1 +=k2
            else :
                if k1 :
                    non_adjacent .append ((i1 ,j1 ,k1 ))
                i1 ,j1 ,k1 =i2 ,j2 ,k2
        if k1 :
            non_adjacent .append ((i1 ,j1 ,k1 ))
        non_adjacent .append ((la ,lb ,0 ))
        self .matching_blocks =list (map (Match ._make ,non_adjacent ))
        return self .matching_blocks
    def get_opcodes (self ):
        if self .opcodes is not None :
            return self .opcodes
        i =j =0
        self .opcodes =answer =[]
        for ai ,bj ,size in self .get_matching_blocks ():
            tag =''
            if i <ai and j <bj :
                tag ='replace'
            elif i <ai :
                tag ='delete'
            elif j <bj :
                tag ='insert'
            if tag :
                answer .append ((tag ,i ,ai ,j ,bj ))
            i ,j =ai +size ,bj +size
            if size :
                answer .append (('equal',ai ,i ,bj ,j ))
        return answer
    def get_grouped_opcodes (self ,n =3 ):
        codes =self .get_opcodes ()
        if not codes :
            codes =[("equal",0 ,1 ,0 ,1 )]
        if codes [0 ][0 ]=='equal':
            tag ,i1 ,i2 ,j1 ,j2 =codes [0 ]
            codes [0 ]=tag ,max (i1 ,i2 -n ),i2 ,max (j1 ,j2 -n ),j2
        if codes [-1 ][0 ]=='equal':
            tag ,i1 ,i2 ,j1 ,j2 =codes [-1 ]
            codes [-1 ]=tag ,i1 ,min (i2 ,i1 +n ),j1 ,min (j2 ,j1 +n )
        nn =n +n
        group =[]
        for tag ,i1 ,i2 ,j1 ,j2 in codes :
            if tag =='equal'and i2 -i1 >nn :
                group .append ((tag ,i1 ,min (i2 ,i1 +n ),j1 ,min (j2 ,j1 +n )))
                yield group
                group =[]
                i1 ,j1 =max (i1 ,i2 -n ),max (j1 ,j2 -n )
            group .append ((tag ,i1 ,i2 ,j1 ,j2 ))
        if group and not (len (group )==1 and group [0 ][0 ]=='equal'):
            yield group
    def ratio (self ):
        matches =sum (triple [-1 ]for triple in self .get_matching_blocks ())
        return _calculate_ratio (matches ,len (self .a )+len (self .b ))
    def quick_ratio (self ):
        if self .fullbcount is None :
            self .fullbcount =fullbcount ={}
            for elt in self .b :
                fullbcount [elt ]=fullbcount .get (elt ,0 )+1
        fullbcount =self .fullbcount
        avail ={}
        availhas ,matches =avail .__contains__ ,0
        for elt in self .a :
            if availhas (elt ):
                numb =avail [elt ]
            else :
                numb =fullbcount .get (elt ,0 )
            avail [elt ]=numb -1
            if numb >0 :
                matches =matches +1
        return _calculate_ratio (matches ,len (self .a )+len (self .b ))
    def real_quick_ratio (self ):
        la ,lb =len (self .a ),len (self .b )
        return _calculate_ratio (min (la ,lb ),la +lb )
    __class_getitem__ =classmethod (GenericAlias )
def get_close_matches (word ,possibilities ,n =3 ,cutoff =0.6 ):
    if not n >0 :
        raise ValueError ("n must be > 0: %r"%(n ,))
    if not 0.0 <=cutoff <=1.0 :
        raise ValueError ("cutoff must be in [0.0, 1.0]: %r"%(cutoff ,))
    result =[]
    s =SequenceMatcher ()
    s .set_seq2 (word )
    for x in possibilities :
        s .set_seq1 (x )
        if s .real_quick_ratio ()>=cutoff and s .quick_ratio ()>=cutoff and s .ratio ()>=cutoff :
            result .append ((s .ratio (),x ))
    result =_nlargest (n ,result )
    return [x for score ,x in result ]
def _keep_original_ws (s ,tag_s ):
    return ''.join (
    c if tag_c ==" "and c .isspace ()else tag_c
    for c ,tag_c in zip (s ,tag_s )
    )
class Differ :
    def __init__ (self ,linejunk =None ,charjunk =None ):
        self .linejunk =linejunk
        self .charjunk =charjunk
    def compare (self ,a ,b ):
        cruncher =SequenceMatcher (self .linejunk ,a ,b )
        for tag ,alo ,ahi ,blo ,bhi in cruncher .get_opcodes ():
            if tag =='replace':
                g =self ._fancy_replace (a ,alo ,ahi ,b ,blo ,bhi )
            elif tag =='delete':
                g =self ._dump ('-',a ,alo ,ahi )
            elif tag =='insert':
                g =self ._dump ('+',b ,blo ,bhi )
            elif tag =='equal':
                g =self ._dump (' ',a ,alo ,ahi )
            else :
                raise ValueError ('unknown tag %r'%(tag ,))
            yield from g
    def _dump (self ,tag ,x ,lo ,hi ):
        for i in range (lo ,hi ):
            yield '%s %s'%(tag ,x [i ])
    def _plain_replace (self ,a ,alo ,ahi ,b ,blo ,bhi ):
        assert alo <ahi and blo <bhi
        if bhi -blo <ahi -alo :
            first =self ._dump ('+',b ,blo ,bhi )
            second =self ._dump ('-',a ,alo ,ahi )
        else :
            first =self ._dump ('-',a ,alo ,ahi )
            second =self ._dump ('+',b ,blo ,bhi )
        for g in first ,second :
            yield from g
    def _fancy_replace (self ,a ,alo ,ahi ,b ,blo ,bhi ):
        best_ratio ,cutoff =0.74 ,0.75
        cruncher =SequenceMatcher (self .charjunk )
        eqi ,eqj =None ,None
        for j in range (blo ,bhi ):
            bj =b [j ]
            cruncher .set_seq2 (bj )
            for i in range (alo ,ahi ):
                ai =a [i ]
                if ai ==bj :
                    if eqi is None :
                        eqi ,eqj =i ,j
                    continue
                cruncher .set_seq1 (ai )
                if cruncher .real_quick_ratio ()>best_ratio and cruncher .quick_ratio ()>best_ratio and cruncher .ratio ()>best_ratio :
                    best_ratio ,best_i ,best_j =cruncher .ratio (),i ,j
        if best_ratio <cutoff :
            if eqi is None :
                yield from self ._plain_replace (a ,alo ,ahi ,b ,blo ,bhi )
                return
            best_i ,best_j ,best_ratio =eqi ,eqj ,1.0
        else :
            eqi =None
        yield from self ._fancy_helper (a ,alo ,best_i ,b ,blo ,best_j )
        aelt ,belt =a [best_i ],b [best_j ]
        if eqi is None :
            atags =btags =""
            cruncher .set_seqs (aelt ,belt )
            for tag ,ai1 ,ai2 ,bj1 ,bj2 in cruncher .get_opcodes ():
                la ,lb =ai2 -ai1 ,bj2 -bj1
                if tag =='replace':
                    atags +='^'*la
                    btags +='^'*lb
                elif tag =='delete':
                    atags +='-'*la
                elif tag =='insert':
                    btags +='+'*lb
                elif tag =='equal':
                    atags +=' '*la
                    btags +=' '*lb
                else :
                    raise ValueError ('unknown tag %r'%(tag ,))
            yield from self ._qformat (aelt ,belt ,atags ,btags )
        else :
            yield '  '+aelt
        yield from self ._fancy_helper (a ,best_i +1 ,ahi ,b ,best_j +1 ,bhi )
    def _fancy_helper (self ,a ,alo ,ahi ,b ,blo ,bhi ):
        g =[]
        if alo <ahi :
            if blo <bhi :
                g =self ._fancy_replace (a ,alo ,ahi ,b ,blo ,bhi )
            else :
                g =self ._dump ('-',a ,alo ,ahi )
        elif blo <bhi :
            g =self ._dump ('+',b ,blo ,bhi )
        yield from g
    def _qformat (self ,aline ,bline ,atags ,btags ):
        atags =_keep_original_ws (aline ,atags ).rstrip ()
        btags =_keep_original_ws (bline ,btags ).rstrip ()
        yield "- "+aline
        if atags :
            yield f"? {atags }\n"
        yield "+ "+bline
        if btags :
            yield f"? {btags }\n"
import re
def IS_LINE_JUNK (line ,pat =re .compile (r"\s*(?:#\s*)?$").match ):
    return pat (line )is not None
def IS_CHARACTER_JUNK (ch ,ws =" \t"):
    return ch in ws
def _format_range_unified (start ,stop ):
    beginning =start +1
    length =stop -start
    if length ==1 :
        return '{}'.format (beginning )
    if not length :
        beginning -=1
    return '{},{}'.format (beginning ,length )
def unified_diff (a ,b ,fromfile ='',tofile ='',fromfiledate ='',
tofiledate ='',n =3 ,lineterm ='\n'):
    _check_types (a ,b ,fromfile ,tofile ,fromfiledate ,tofiledate ,lineterm )
    started =False
    for group in SequenceMatcher (None ,a ,b ).get_grouped_opcodes (n ):
        if not started :
            started =True
            fromdate ='\t{}'.format (fromfiledate )if fromfiledate else ''
            todate ='\t{}'.format (tofiledate )if tofiledate else ''
            yield '--- {}{}{}'.format (fromfile ,fromdate ,lineterm )
            yield '+++ {}{}{}'.format (tofile ,todate ,lineterm )
        first ,last =group [0 ],group [-1 ]
        file1_range =_format_range_unified (first [1 ],last [2 ])
        file2_range =_format_range_unified (first [3 ],last [4 ])
        yield '@@ -{} +{} @@{}'.format (file1_range ,file2_range ,lineterm )
        for tag ,i1 ,i2 ,j1 ,j2 in group :
            if tag =='equal':
                for line in a [i1 :i2 ]:
                    yield ' '+line
                continue
            if tag in {'replace','delete'}:
                for line in a [i1 :i2 ]:
                    yield '-'+line
            if tag in {'replace','insert'}:
                for line in b [j1 :j2 ]:
                    yield '+'+line
def _format_range_context (start ,stop ):
    beginning =start +1
    length =stop -start
    if not length :
        beginning -=1
    if length <=1 :
        return '{}'.format (beginning )
    return '{},{}'.format (beginning ,beginning +length -1 )
def context_diff (a ,b ,fromfile ='',tofile ='',
fromfiledate ='',tofiledate ='',n =3 ,lineterm ='\n'):
    _check_types (a ,b ,fromfile ,tofile ,fromfiledate ,tofiledate ,lineterm )
    prefix =dict (insert ='+ ',delete ='- ',replace ='! ',equal ='  ')
    started =False
    for group in SequenceMatcher (None ,a ,b ).get_grouped_opcodes (n ):
        if not started :
            started =True
            fromdate ='\t{}'.format (fromfiledate )if fromfiledate else ''
            todate ='\t{}'.format (tofiledate )if tofiledate else ''
            yield '*** {}{}{}'.format (fromfile ,fromdate ,lineterm )
            yield '--- {}{}{}'.format (tofile ,todate ,lineterm )
        first ,last =group [0 ],group [-1 ]
        yield '***************'+lineterm
        file1_range =_format_range_context (first [1 ],last [2 ])
        yield '*** {} ****{}'.format (file1_range ,lineterm )
        if any (tag in {'replace','delete'}for tag ,_ ,_ ,_ ,_ in group ):
            for tag ,i1 ,i2 ,_ ,_ in group :
                if tag !='insert':
                    for line in a [i1 :i2 ]:
                        yield prefix [tag ]+line
        file2_range =_format_range_context (first [3 ],last [4 ])
        yield '--- {} ----{}'.format (file2_range ,lineterm )
        if any (tag in {'replace','insert'}for tag ,_ ,_ ,_ ,_ in group ):
            for tag ,_ ,_ ,j1 ,j2 in group :
                if tag !='delete':
                    for line in b [j1 :j2 ]:
                        yield prefix [tag ]+line
def _check_types (a ,b ,*args ):
    if a and not isinstance (a [0 ],str ):
        raise TypeError ('lines to compare must be str, not %s (%r)'%
        (type (a [0 ]).__name__ ,a [0 ]))
    if b and not isinstance (b [0 ],str ):
        raise TypeError ('lines to compare must be str, not %s (%r)'%
        (type (b [0 ]).__name__ ,b [0 ]))
    for arg in args :
        if not isinstance (arg ,str ):
            raise TypeError ('all arguments must be str, not: %r'%(arg ,))
def diff_bytes (dfunc ,a ,b ,fromfile =b'',tofile =b'',
fromfiledate =b'',tofiledate =b'',n =3 ,lineterm =b'\n'):
    def decode (s ):
        try :
            return s .decode ('ascii','surrogateescape')
        except AttributeError as err :
            msg =('all arguments must be bytes, not %s (%r)'%
            (type (s ).__name__ ,s ))
            raise TypeError (msg )from err
    a =list (map (decode ,a ))
    b =list (map (decode ,b ))
    fromfile =decode (fromfile )
    tofile =decode (tofile )
    fromfiledate =decode (fromfiledate )
    tofiledate =decode (tofiledate )
    lineterm =decode (lineterm )
    lines =dfunc (a ,b ,fromfile ,tofile ,fromfiledate ,tofiledate ,n ,lineterm )
    for line in lines :
        yield line .encode ('ascii','surrogateescape')
def ndiff (a ,b ,linejunk =None ,charjunk =IS_CHARACTER_JUNK ):
    return Differ (linejunk ,charjunk ).compare (a ,b )
def _mdiff (fromlines ,tolines ,context =None ,linejunk =None ,
charjunk =IS_CHARACTER_JUNK ):
    import re
    change_re =re .compile (r'(\++|\-+|\^+)')
    diff_lines_iterator =ndiff (fromlines ,tolines ,linejunk ,charjunk )
    def _make_line (lines ,format_key ,side ,num_lines =[0 ,0 ]):
        num_lines [side ]+=1
        if format_key is None :
            return (num_lines [side ],lines .pop (0 )[2 :])
        if format_key =='?':
            text ,markers =lines .pop (0 ),lines .pop (0 )
            sub_info =[]
            def record_sub_info (match_object ,sub_info =sub_info ):
                sub_info .append ([match_object .group (1 )[0 ],match_object .span ()])
                return match_object .group (1 )
            change_re .sub (record_sub_info ,markers )
            for key ,(begin ,end )in reversed (sub_info ):
                text =text [0 :begin ]+'\0'+key +text [begin :end ]+'\1'+text [end :]
            text =text [2 :]
        else :
            text =lines .pop (0 )[2 :]
            if not text :
                text =' '
            text ='\0'+format_key +text +'\1'
        return (num_lines [side ],text )
    def _line_iterator ():
        lines =[]
        num_blanks_pending ,num_blanks_to_yield =0 ,0
        while True :
            while len (lines )<4 :
                lines .append (next (diff_lines_iterator ,'X'))
            s =''.join ([line [0 ]for line in lines ])
            if s .startswith ('X'):
                num_blanks_to_yield =num_blanks_pending
            elif s .startswith ('-?+?'):
                yield _make_line (lines ,'?',0 ),_make_line (lines ,'?',1 ),True
                continue
            elif s .startswith ('--++'):
                num_blanks_pending -=1
                yield _make_line (lines ,'-',0 ),None ,True
                continue
            elif s .startswith (('--?+','--+','- ')):
                from_line ,to_line =_make_line (lines ,'-',0 ),None
                num_blanks_to_yield ,num_blanks_pending =num_blanks_pending -1 ,0
            elif s .startswith ('-+?'):
                yield _make_line (lines ,None ,0 ),_make_line (lines ,'?',1 ),True
                continue
            elif s .startswith ('-?+'):
                yield _make_line (lines ,'?',0 ),_make_line (lines ,None ,1 ),True
                continue
            elif s .startswith ('-'):
                num_blanks_pending -=1
                yield _make_line (lines ,'-',0 ),None ,True
                continue
            elif s .startswith ('+--'):
                num_blanks_pending +=1
                yield None ,_make_line (lines ,'+',1 ),True
                continue
            elif s .startswith (('+ ','+-')):
                from_line ,to_line =None ,_make_line (lines ,'+',1 )
                num_blanks_to_yield ,num_blanks_pending =num_blanks_pending +1 ,0
            elif s .startswith ('+'):
                num_blanks_pending +=1
                yield None ,_make_line (lines ,'+',1 ),True
                continue
            elif s .startswith (' '):
                yield _make_line (lines [:],None ,0 ),_make_line (lines ,None ,1 ),False
                continue
            while (num_blanks_to_yield <0 ):
                num_blanks_to_yield +=1
                yield None ,('','\n'),True
            while (num_blanks_to_yield >0 ):
                num_blanks_to_yield -=1
                yield ('','\n'),None ,True
            if s .startswith ('X'):
                return
            else :
                yield from_line ,to_line ,True
    def _line_pair_iterator ():
        line_iterator =_line_iterator ()
        fromlines ,tolines =[],[]
        while True :
            while (len (fromlines )==0 or len (tolines )==0 ):
                try :
                    from_line ,to_line ,found_diff =next (line_iterator )
                except StopIteration :
                    return
                if from_line is not None :
                    fromlines .append ((from_line ,found_diff ))
                if to_line is not None :
                    tolines .append ((to_line ,found_diff ))
            from_line ,fromDiff =fromlines .pop (0 )
            to_line ,to_diff =tolines .pop (0 )
            yield (from_line ,to_line ,fromDiff or to_diff )
    line_pair_iterator =_line_pair_iterator ()
    if context is None :
        yield from line_pair_iterator
    else :
        context +=1
        lines_to_write =0
        while True :
            index ,contextLines =0 ,[None ]*(context )
            found_diff =False
            while (found_diff is False ):
                try :
                    from_line ,to_line ,found_diff =next (line_pair_iterator )
                except StopIteration :
                    return
                i =index %context
                contextLines [i ]=(from_line ,to_line ,found_diff )
                index +=1
            if index >context :
                yield None ,None ,None
                lines_to_write =context
            else :
                lines_to_write =index
                index =0
            while (lines_to_write ):
                i =index %context
                index +=1
                yield contextLines [i ]
                lines_to_write -=1
            lines_to_write =context -1
            try :
                while (lines_to_write ):
                    from_line ,to_line ,found_diff =next (line_pair_iterator )
                    if found_diff :
                        lines_to_write =context -1
                    else :
                        lines_to_write -=1
                    yield from_line ,to_line ,found_diff
            except StopIteration :
                return
_file_template ="""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=%(charset)s" />
    <title></title>
    <style type="text/css">%(styles)s
    </style>
</head>
<body>
    %(table)s%(legend)s
</body>
</html>"""
_styles ="""
        table.diff {font-family: Menlo, Consolas, Monaco, Liberation Mono, Lucida Console, monospace; border:medium}
        .diff_header {background-color:#e0e0e0}
        td.diff_header {text-align:right}
        .diff_next {background-color:#c0c0c0}
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}"""
_table_template ="""
    <table class="diff" id="difflib_chg_%(prefix)s_top"
           cellspacing="0" cellpadding="0" rules="groups" >
        <colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>
        <colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>
        %(header_row)s
        <tbody>
%(data_rows)s        </tbody>
    </table>"""
_legend ="""
    <table class="diff" summary="Legends">
        <tr> <th colspan="2"> Legends </th> </tr>
        <tr> <td> <table border="" summary="Colors">
                      <tr><th> Colors </th> </tr>
                      <tr><td class="diff_add">&nbsp;Added&nbsp;</td></tr>
                      <tr><td class="diff_chg">Changed</td> </tr>
                      <tr><td class="diff_sub">Deleted</td> </tr>
                  </table></td>
             <td> <table border="" summary="Links">
                      <tr><th colspan="2"> Links </th> </tr>
                      <tr><td>(f)irst change</td> </tr>
                      <tr><td>(n)ext change</td> </tr>
                      <tr><td>(t)op</td> </tr>
                  </table></td> </tr>
    </table>"""
class HtmlDiff (object ):
    _file_template =_file_template
    _styles =_styles
    _table_template =_table_template
    _legend =_legend
    _default_prefix =0
    def __init__ (self ,tabsize =8 ,wrapcolumn =None ,linejunk =None ,
    charjunk =IS_CHARACTER_JUNK ):
        self ._tabsize =tabsize
        self ._wrapcolumn =wrapcolumn
        self ._linejunk =linejunk
        self ._charjunk =charjunk
    def make_file (self ,fromlines ,tolines ,fromdesc ='',todesc ='',
    context =False ,numlines =5 ,*,charset ='utf-8'):
        return (self ._file_template %dict (
        styles =self ._styles ,
        legend =self ._legend ,
        table =self .make_table (fromlines ,tolines ,fromdesc ,todesc ,
        context =context ,numlines =numlines ),
        charset =charset
        )).encode (charset ,'xmlcharrefreplace').decode (charset )
    def _tab_newline_replace (self ,fromlines ,tolines ):
        def expand_tabs (line ):
            line =line .replace (' ','\0')
            line =line .expandtabs (self ._tabsize )
            line =line .replace (' ','\t')
            return line .replace ('\0',' ').rstrip ('\n')
        fromlines =[expand_tabs (line )for line in fromlines ]
        tolines =[expand_tabs (line )for line in tolines ]
        return fromlines ,tolines
    def _split_line (self ,data_list ,line_num ,text ):
        if not line_num :
            data_list .append ((line_num ,text ))
            return
        size =len (text )
        max =self ._wrapcolumn
        if (size <=max )or ((size -(text .count ('\0')*3 ))<=max ):
            data_list .append ((line_num ,text ))
            return
        i =0
        n =0
        mark =''
        while n <max and i <size :
            if text [i ]=='\0':
                i +=1
                mark =text [i ]
                i +=1
            elif text [i ]=='\1':
                i +=1
                mark =''
            else :
                i +=1
                n +=1
        line1 =text [:i ]
        line2 =text [i :]
        if mark :
            line1 =line1 +'\1'
            line2 ='\0'+mark +line2
        data_list .append ((line_num ,line1 ))
        self ._split_line (data_list ,'>',line2 )
    def _line_wrapper (self ,diffs ):
        for fromdata ,todata ,flag in diffs :
            if flag is None :
                yield fromdata ,todata ,flag
                continue
            (fromline ,fromtext ),(toline ,totext )=fromdata ,todata
            fromlist ,tolist =[],[]
            self ._split_line (fromlist ,fromline ,fromtext )
            self ._split_line (tolist ,toline ,totext )
            while fromlist or tolist :
                if fromlist :
                    fromdata =fromlist .pop (0 )
                else :
                    fromdata =('',' ')
                if tolist :
                    todata =tolist .pop (0 )
                else :
                    todata =('',' ')
                yield fromdata ,todata ,flag
    def _collect_lines (self ,diffs ):
        fromlist ,tolist ,flaglist =[],[],[]
        for fromdata ,todata ,flag in diffs :
            try :
                fromlist .append (self ._format_line (0 ,flag ,*fromdata ))
                tolist .append (self ._format_line (1 ,flag ,*todata ))
            except TypeError :
                fromlist .append (None )
                tolist .append (None )
            flaglist .append (flag )
        return fromlist ,tolist ,flaglist
    def _format_line (self ,side ,flag ,linenum ,text ):
        try :
            linenum ='%d'%linenum
            id =' id="%s%s"'%(self ._prefix [side ],linenum )
        except TypeError :
            id =''
        text =text .replace ("&","&amp;").replace (">","&gt;").replace ("<","&lt;")
        text =text .replace (' ','&nbsp;').rstrip ()
        return '<td class="diff_header"%s>%s</td><td nowrap="nowrap">%s</td>'%(id ,linenum ,text )
    def _make_prefix (self ):
        fromprefix ="from%d_"%HtmlDiff ._default_prefix
        toprefix ="to%d_"%HtmlDiff ._default_prefix
        HtmlDiff ._default_prefix +=1
        self ._prefix =[fromprefix ,toprefix ]
    def _convert_flags (self ,fromlist ,tolist ,flaglist ,context ,numlines ):
        toprefix =self ._prefix [1 ]
        next_id =['']*len (flaglist )
        next_href =['']*len (flaglist )
        num_chg ,in_change =0 ,False
        last =0
        for i ,flag in enumerate (flaglist ):
            if flag :
                if not in_change :
                    in_change =True
                    last =i
                    i =max ([0 ,i -numlines ])
                    next_id [i ]=' id="difflib_chg_%s_%d"'%(toprefix ,num_chg )
                    num_chg +=1
                    next_href [last ]='<a href="#difflib_chg_%s_%d">n</a>'%(
                    toprefix ,num_chg )
            else :
                in_change =False
        if not flaglist :
            flaglist =[False ]
            next_id =['']
            next_href =['']
            last =0
            if context :
                fromlist =['<td></td><td>&nbsp;No Differences Found&nbsp;</td>']
                tolist =fromlist
            else :
                fromlist =tolist =['<td></td><td>&nbsp;Empty File&nbsp;</td>']
        if not flaglist [0 ]:
            next_href [0 ]='<a href="#difflib_chg_%s_0">f</a>'%toprefix
        next_href [last ]='<a href="#difflib_chg_%s_top">t</a>'%(toprefix )
        return fromlist ,tolist ,flaglist ,next_href ,next_id
    def make_table (self ,fromlines ,tolines ,fromdesc ='',todesc ='',context =False ,
    numlines =5 ):
        self ._make_prefix ()
        fromlines ,tolines =self ._tab_newline_replace (fromlines ,tolines )
        if context :
            context_lines =numlines
        else :
            context_lines =None
        diffs =_mdiff (fromlines ,tolines ,context_lines ,linejunk =self ._linejunk ,
        charjunk =self ._charjunk )
        if self ._wrapcolumn :
            diffs =self ._line_wrapper (diffs )
        fromlist ,tolist ,flaglist =self ._collect_lines (diffs )
        fromlist ,tolist ,flaglist ,next_href ,next_id =self ._convert_flags (
        fromlist ,tolist ,flaglist ,context ,numlines )
        s =[]
        fmt ='            <tr><td class="diff_next"%s>%s</td>%s'+'<td class="diff_next">%s</td>%s</tr>\n'
        for i in range (len (flaglist )):
            if flaglist [i ]is None :
                if i >0 :
                    s .append ('        </tbody>        \n        <tbody>\n')
            else :
                s .append (fmt %(next_id [i ],next_href [i ],fromlist [i ],
                next_href [i ],tolist [i ]))
        if fromdesc or todesc :
            header_row ='<thead><tr>%s%s%s%s</tr></thead>'%(
            "",
            ""%fromdesc ,
            "",
            ""%todesc )
        else :
            header_row =''
        table =self ._table_template %dict (
        data_rows =''.join (s ),
        header_row =header_row ,
        prefix =self ._prefix [1 ])
        return table .replace ('\0+','<span class="diff_add">').replace ('\0-','<span class="diff_sub">').replace ('\0^','<span class="diff_chg">').replace ('\1','</span>').replace ('\t','&nbsp;')
del re
def restore (delta ,which ):
    try :
        tag ={1 :"- ",2 :"+ "}[int (which )]
    except KeyError :
        raise ValueError ('unknown delta choice (must be 1 or 2): %r'
        %which )from None
    prefixes =("  ",tag )
    for line in delta :
        if line [:2 ]in prefixes :
            yield line [2 :]
def _test ():
    import doctest ,difflib
    return doctest .testmod (difflib )
if __name__ =="__main__":
    _test ()
__all__ =['update_wrapper','wraps','WRAPPER_ASSIGNMENTS','WRAPPER_UPDATES',
"",'cache','cmp_to_key','lru_cache','reduce',
"",'partialmethod','singledispatch','singledispatchmethod',
""]
from abc import get_cache_token
from collections import namedtuple
from reprlib import recursive_repr
from _thread import RLock
GenericAlias =type (list [int ])
WRAPPER_ASSIGNMENTS =('__module__','__name__','__qualname__','__doc__',
"",'__type_params__')
WRAPPER_UPDATES =('__dict__',)
def update_wrapper (wrapper ,
wrapped ,
assigned =WRAPPER_ASSIGNMENTS ,
updated =WRAPPER_UPDATES ):
    for attr in assigned :
        try :
            value =getattr (wrapped ,attr )
        except AttributeError :
            pass
        else :
            setattr (wrapper ,attr ,value )
    for attr in updated :
        getattr (wrapper ,attr ).update (getattr (wrapped ,attr ,{}))
    wrapper .__wrapped__ =wrapped
    return wrapper
def wraps (wrapped ,
assigned =WRAPPER_ASSIGNMENTS ,
updated =WRAPPER_UPDATES ):
    return partial (update_wrapper ,wrapped =wrapped ,
    assigned =assigned ,updated =updated )
def _gt_from_lt (self ,other ):
    op_result =type (self ).__lt__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result and self !=other
def _le_from_lt (self ,other ):
    op_result =type (self ).__lt__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return op_result or self ==other
def _ge_from_lt (self ,other ):
    op_result =type (self ).__lt__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result
def _ge_from_le (self ,other ):
    op_result =type (self ).__le__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result or self ==other
def _lt_from_le (self ,other ):
    op_result =type (self ).__le__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return op_result and self !=other
def _gt_from_le (self ,other ):
    op_result =type (self ).__le__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result
def _lt_from_gt (self ,other ):
    op_result =type (self ).__gt__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result and self !=other
def _ge_from_gt (self ,other ):
    op_result =type (self ).__gt__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return op_result or self ==other
def _le_from_gt (self ,other ):
    op_result =type (self ).__gt__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result
def _le_from_ge (self ,other ):
    op_result =type (self ).__ge__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result or self ==other
def _gt_from_ge (self ,other ):
    op_result =type (self ).__ge__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return op_result and self !=other
def _lt_from_ge (self ,other ):
    op_result =type (self ).__ge__ (self ,other )
    if op_result is NotImplemented :
        return op_result
    return not op_result
_convert ={
"":[('__gt__',_gt_from_lt ),
('__le__',_le_from_lt ),
('__ge__',_ge_from_lt )],
"":[('__ge__',_ge_from_le ),
('__lt__',_lt_from_le ),
('__gt__',_gt_from_le )],
"":[('__lt__',_lt_from_gt ),
('__ge__',_ge_from_gt ),
('__le__',_le_from_gt )],
"":[('__le__',_le_from_ge ),
('__gt__',_gt_from_ge ),
('__lt__',_lt_from_ge )]
}
def total_ordering (cls ):
    roots ={op for op in _convert if getattr (cls ,op ,None )is not getattr (object ,op ,None )}
    if not roots :
        raise ValueError ('must define at least one ordering operation: < > <= >=')
    root =max (roots )
    for opname ,opfunc in _convert [root ]:
        if opname not in roots :
            opfunc .__name__ =opname
            setattr (cls ,opname ,opfunc )
    return cls
def cmp_to_key (mycmp ):
    class K (object ):
        __slots__ =['obj']
        def __init__ (self ,obj ):
            self .obj =obj
        def __lt__ (self ,other ):
            return mycmp (self .obj ,other .obj )<0
        def __gt__ (self ,other ):
            return mycmp (self .obj ,other .obj )>0
        def __eq__ (self ,other ):
            return mycmp (self .obj ,other .obj )==0
        def __le__ (self ,other ):
            return mycmp (self .obj ,other .obj )<=0
        def __ge__ (self ,other ):
            return mycmp (self .obj ,other .obj )>=0
        __hash__ =None
    return K
try :
    from _functools import cmp_to_key
except ImportError :
    pass
_initial_missing =object ()
def reduce (function ,sequence ,initial =_initial_missing ):
    it =iter (sequence )
    if initial is _initial_missing :
        try :
            value =next (it )
        except StopIteration :
            raise TypeError (
            "")from None
    else :
        value =initial
    for element in it :
        value =function (value ,element )
    return value
try :
    from _functools import reduce
except ImportError :
    pass
class partial :
    __slots__ ="func","args","keywords","__dict__","__weakref__"
    def __new__ (cls ,func ,/,*args ,**keywords ):
        if not callable (func ):
            raise TypeError ("the first argument must be callable")
        if isinstance (func ,partial ):
            args =func .args +args
            keywords ={**func .keywords ,**keywords }
            func =func .func
        self =super (partial ,cls ).__new__ (cls )
        self .func =func
        self .args =args
        self .keywords =keywords
        return self
    def __call__ (self ,/,*args ,**keywords ):
        keywords ={**self .keywords ,**keywords }
        return self .func (*self .args ,*args ,**keywords )
    @recursive_repr ()
    def __repr__ (self ):
        cls =type (self )
        qualname =cls .__qualname__
        module =cls .__module__
        args =[repr (self .func )]
        args .extend (repr (x )for x in self .args )
        args .extend (f"{k }={v !r }"for (k ,v )in self .keywords .items ())
        return f"{module }.{qualname }({', '.join (args )})"
    def __get__ (self ,obj ,objtype =None ):
        if obj is None :
            return self
        import warnings
        warnings .warn ('functools.partial will be a method descriptor in '
        "",
        FutureWarning ,2 )
        return self
    def __reduce__ (self ):
        return type (self ),(self .func ,),(self .func ,self .args ,
        self .keywords or None ,self .__dict__ or None )
    def __setstate__ (self ,state ):
        if not isinstance (state ,tuple ):
            raise TypeError ("argument to __setstate__ must be a tuple")
        if len (state )!=4 :
            raise TypeError (f"expected 4 items in state, got {len (state )}")
        func ,args ,kwds ,namespace =state
        if (not callable (func )or not isinstance (args ,tuple )or
        (kwds is not None and not isinstance (kwds ,dict ))or
        (namespace is not None and not isinstance (namespace ,dict ))):
            raise TypeError ("invalid partial state")
        args =tuple (args )
        if kwds is None :
            kwds ={}
        elif type (kwds )is not dict :
            kwds =dict (kwds )
        if namespace is None :
            namespace ={}
        self .__dict__ =namespace
        self .func =func
        self .args =args
        self .keywords =kwds
    __class_getitem__ =classmethod (GenericAlias )
try :
    from _functools import partial
except ImportError :
    pass
class partialmethod (object ):
    def __init__ (self ,func ,/,*args ,**keywords ):
        if not callable (func )and not hasattr (func ,"__get__"):
            raise TypeError ("{!r} is not callable or a descriptor"
            .format (func ))
        if isinstance (func ,partialmethod ):
            self .func =func .func
            self .args =func .args +args
            self .keywords ={**func .keywords ,**keywords }
        else :
            self .func =func
            self .args =args
            self .keywords =keywords
    def __repr__ (self ):
        cls =type (self )
        module =cls .__module__
        qualname =cls .__qualname__
        args =[repr (self .func )]
        args .extend (map (repr ,self .args ))
        args .extend (f"{k }={v !r }"for k ,v in self .keywords .items ())
        return f"{module }.{qualname }({', '.join (args )})"
    def _make_unbound_method (self ):
        def _method (cls_or_self ,/,*args ,**keywords ):
            keywords ={**self .keywords ,**keywords }
            return self .func (cls_or_self ,*self .args ,*args ,**keywords )
        _method .__isabstractmethod__ =self .__isabstractmethod__
        _method .__partialmethod__ =self
        return _method
    def __get__ (self ,obj ,cls =None ):
        get =getattr (self .func ,"__get__",None )
        result =None
        if get is not None and not isinstance (self .func ,partial ):
            new_func =get (obj ,cls )
            if new_func is not self .func :
                result =partial (new_func ,*self .args ,**self .keywords )
                try :
                    result .__self__ =new_func .__self__
                except AttributeError :
                    pass
        if result is None :
            result =self ._make_unbound_method ().__get__ (obj ,cls )
        return result
    @property
    def __isabstractmethod__ (self ):
        return getattr (self .func ,"__isabstractmethod__",False )
    __class_getitem__ =classmethod (GenericAlias )
def _unwrap_partial (func ):
    while isinstance (func ,partial ):
        func =func .func
    return func
def _unwrap_partialmethod (func ):
    prev =None
    while func is not prev :
        prev =func
        while isinstance (getattr (func ,"__partialmethod__",None ),partialmethod ):
            func =func .__partialmethod__
        while isinstance (func ,partialmethod ):
            func =getattr (func ,'func')
        func =_unwrap_partial (func )
    return func
_CacheInfo =namedtuple ("CacheInfo",["hits","misses","maxsize","currsize"])
class _HashedSeq (list ):
    __slots__ ='hashvalue'
    def __init__ (self ,tup ,hash =hash ):
        self [:]=tup
        self .hashvalue =hash (tup )
    def __hash__ (self ):
        return self .hashvalue
def _make_key (args ,kwds ,typed ,
kwd_mark =(object (),),
fasttypes ={int ,str },
tuple =tuple ,type =type ,len =len ):
    key =args
    if kwds :
        key +=kwd_mark
        for item in kwds .items ():
            key +=item
    if typed :
        key +=tuple (type (v )for v in args )
        if kwds :
            key +=tuple (type (v )for v in kwds .values ())
    elif len (key )==1 and type (key [0 ])in fasttypes :
        return key [0 ]
    return _HashedSeq (key )
def lru_cache (maxsize =128 ,typed =False ):
    if isinstance (maxsize ,int ):
        if maxsize <0 :
            maxsize =0
    elif callable (maxsize )and isinstance (typed ,bool ):
        user_function ,maxsize =maxsize ,128
        wrapper =_lru_cache_wrapper (user_function ,maxsize ,typed ,_CacheInfo )
        wrapper .cache_parameters =lambda :{'maxsize':maxsize ,'typed':typed }
        return update_wrapper (wrapper ,user_function )
    elif maxsize is not None :
        raise TypeError (
        "")
    def decorating_function (user_function ):
        wrapper =_lru_cache_wrapper (user_function ,maxsize ,typed ,_CacheInfo )
        wrapper .cache_parameters =lambda :{'maxsize':maxsize ,'typed':typed }
        return update_wrapper (wrapper ,user_function )
    return decorating_function
def _lru_cache_wrapper (user_function ,maxsize ,typed ,_CacheInfo ):
    sentinel =object ()
    make_key =_make_key
    PREV ,NEXT ,KEY ,RESULT =0 ,1 ,2 ,3
    cache ={}
    hits =misses =0
    full =False
    cache_get =cache .get
    cache_len =cache .__len__
    lock =RLock ()
    root =[]
    root [:]=[root ,root ,None ,None ]
    if maxsize ==0 :
        def wrapper (*args ,**kwds ):
            nonlocal misses
            misses +=1
            result =user_function (*args ,**kwds )
            return result
    elif maxsize is None :
        def wrapper (*args ,**kwds ):
            nonlocal hits ,misses
            key =make_key (args ,kwds ,typed )
            result =cache_get (key ,sentinel )
            if result is not sentinel :
                hits +=1
                return result
            misses +=1
            result =user_function (*args ,**kwds )
            cache [key ]=result
            return result
    else :
        def wrapper (*args ,**kwds ):
            nonlocal root ,hits ,misses ,full
            key =make_key (args ,kwds ,typed )
            with lock :
                link =cache_get (key )
                if link is not None :
                    link_prev ,link_next ,_key ,result =link
                    link_prev [NEXT ]=link_next
                    link_next [PREV ]=link_prev
                    last =root [PREV ]
                    last [NEXT ]=root [PREV ]=link
                    link [PREV ]=last
                    link [NEXT ]=root
                    hits +=1
                    return result
                misses +=1
            result =user_function (*args ,**kwds )
            with lock :
                if key in cache :
                    pass
                elif full :
                    oldroot =root
                    oldroot [KEY ]=key
                    oldroot [RESULT ]=result
                    root =oldroot [NEXT ]
                    oldkey =root [KEY ]
                    oldresult =root [RESULT ]
                    root [KEY ]=root [RESULT ]=None
                    del cache [oldkey ]
                    cache [key ]=oldroot
                else :
                    last =root [PREV ]
                    link =[last ,root ,key ,result ]
                    last [NEXT ]=root [PREV ]=cache [key ]=link
                    full =(cache_len ()>=maxsize )
            return result
    def cache_info ():
        with lock :
            return _CacheInfo (hits ,misses ,maxsize ,cache_len ())
    def cache_clear ():
        nonlocal hits ,misses ,full
        with lock :
            cache .clear ()
            root [:]=[root ,root ,None ,None ]
            hits =misses =0
            full =False
    wrapper .cache_info =cache_info
    wrapper .cache_clear =cache_clear
    return wrapper
try :
    from _functools import _lru_cache_wrapper
except ImportError :
    pass
def cache (user_function ,/):
    return lru_cache (maxsize =None )(user_function )
def _c3_merge (sequences ):
    result =[]
    while True :
        sequences =[s for s in sequences if s ]
        if not sequences :
            return result
        for s1 in sequences :
            candidate =s1 [0 ]
            for s2 in sequences :
                if candidate in s2 [1 :]:
                    candidate =None
                    break
            else :
                break
        if candidate is None :
            raise RuntimeError ("Inconsistent hierarchy")
        result .append (candidate )
        for seq in sequences :
            if seq [0 ]==candidate :
                del seq [0 ]
def _c3_mro (cls ,abcs =None ):
    for i ,base in enumerate (reversed (cls .__bases__ )):
        if hasattr (base ,'__abstractmethods__'):
            boundary =len (cls .__bases__ )-i
            break
    else :
        boundary =0
    abcs =list (abcs )if abcs else []
    explicit_bases =list (cls .__bases__ [:boundary ])
    abstract_bases =[]
    other_bases =list (cls .__bases__ [boundary :])
    for base in abcs :
        if issubclass (cls ,base )and not any (
        issubclass (b ,base )for b in cls .__bases__
        ):
            abstract_bases .append (base )
    for base in abstract_bases :
        abcs .remove (base )
    explicit_c3_mros =[_c3_mro (base ,abcs =abcs )for base in explicit_bases ]
    abstract_c3_mros =[_c3_mro (base ,abcs =abcs )for base in abstract_bases ]
    other_c3_mros =[_c3_mro (base ,abcs =abcs )for base in other_bases ]
    return _c3_merge (
    [[cls ]]+
    explicit_c3_mros +abstract_c3_mros +other_c3_mros +
    [explicit_bases ]+[abstract_bases ]+[other_bases ]
    )
def _compose_mro (cls ,types ):
    bases =set (cls .__mro__ )
    def is_related (typ ):
        return (typ not in bases and hasattr (typ ,'__mro__')
        and not isinstance (typ ,GenericAlias )
        and issubclass (cls ,typ ))
    types =[n for n in types if is_related (n )]
    def is_strict_base (typ ):
        for other in types :
            if typ !=other and typ in other .__mro__ :
                return True
        return False
    types =[n for n in types if not is_strict_base (n )]
    type_set =set (types )
    mro =[]
    for typ in types :
        found =[]
        for sub in typ .__subclasses__ ():
            if sub not in bases and issubclass (cls ,sub ):
                found .append ([s for s in sub .__mro__ if s in type_set ])
        if not found :
            mro .append (typ )
            continue
        found .sort (key =len ,reverse =True )
        for sub in found :
            for subcls in sub :
                if subcls not in mro :
                    mro .append (subcls )
    return _c3_mro (cls ,abcs =mro )
def _find_impl (cls ,registry ):
    mro =_compose_mro (cls ,registry .keys ())
    match =None
    for t in mro :
        if match is not None :
            if (t in registry and t not in cls .__mro__
            and match not in cls .__mro__
            and not issubclass (match ,t )):
                raise RuntimeError ("Ambiguous dispatch: {} or {}".format (
                match ,t ))
            break
        if t in registry :
            match =t
    return registry .get (match )
def singledispatch (func ):
    import types ,weakref
    registry ={}
    dispatch_cache =weakref .WeakKeyDictionary ()
    cache_token =None
    def dispatch (cls ):
        nonlocal cache_token
        if cache_token is not None :
            current_token =get_cache_token ()
            if cache_token !=current_token :
                dispatch_cache .clear ()
                cache_token =current_token
        try :
            impl =dispatch_cache [cls ]
        except KeyError :
            try :
                impl =registry [cls ]
            except KeyError :
                impl =_find_impl (cls ,registry )
            dispatch_cache [cls ]=impl
        return impl
    def _is_union_type (cls ):
        from typing import get_origin ,Union
        return get_origin (cls )in {Union ,types .UnionType }
    def _is_valid_dispatch_type (cls ):
        if isinstance (cls ,type ):
            return True
        from typing import get_args
        return (_is_union_type (cls )and
        all (isinstance (arg ,type )for arg in get_args (cls )))
    def register (cls ,func =None ):
        nonlocal cache_token
        if _is_valid_dispatch_type (cls ):
            if func is None :
                return lambda f :register (cls ,f )
        else :
            if func is not None :
                raise TypeError (
                f"Invalid first argument to `register()`. "
                f"{cls !r } is not a class or union type."
                )
            ann =getattr (cls ,'__annotations__',{})
            if not ann :
                raise TypeError (
                f"Invalid first argument to `register()`: {cls !r }. "
                f"Use either `@register(some_class)` or plain `@register` "
                f"on an annotated function."
                )
            func =cls
            from typing import get_type_hints
            argname ,cls =next (iter (get_type_hints (func ).items ()))
            if not _is_valid_dispatch_type (cls ):
                if _is_union_type (cls ):
                    raise TypeError (
                    f"Invalid annotation for {argname !r }. "
                    f"{cls !r } not all arguments are classes."
                    )
                else :
                    raise TypeError (
                    f"Invalid annotation for {argname !r }. "
                    f"{cls !r } is not a class."
                    )
        if _is_union_type (cls ):
            from typing import get_args
            for arg in get_args (cls ):
                registry [arg ]=func
        else :
            registry [cls ]=func
        if cache_token is None and hasattr (cls ,'__abstractmethods__'):
            cache_token =get_cache_token ()
        dispatch_cache .clear ()
        return func
    def wrapper (*args ,**kw ):
        if not args :
            raise TypeError (f'{funcname } requires at least '
            "")
        return dispatch (args [0 ].__class__ )(*args ,**kw )
    funcname =getattr (func ,'__name__','singledispatch function')
    registry [object ]=func
    wrapper .register =register
    wrapper .dispatch =dispatch
    wrapper .registry =types .MappingProxyType (registry )
    wrapper ._clear_cache =dispatch_cache .clear
    update_wrapper (wrapper ,func )
    return wrapper
class singledispatchmethod :
    def __init__ (self ,func ):
        if not callable (func )and not hasattr (func ,"__get__"):
            raise TypeError (f"{func !r } is not callable or a descriptor")
        self .dispatcher =singledispatch (func )
        self .func =func
    def register (self ,cls ,method =None ):
        return self .dispatcher .register (cls ,func =method )
    def __get__ (self ,obj ,cls =None ):
        dispatch =self .dispatcher .dispatch
        funcname =getattr (self .func ,'__name__','singledispatchmethod method')
        def _method (*args ,**kwargs ):
            if not args :
                raise TypeError (f'{funcname } requires at least '
                "")
            return dispatch (args [0 ].__class__ ).__get__ (obj ,cls )(*args ,**kwargs )
        _method .__isabstractmethod__ =self .__isabstractmethod__
        _method .register =self .register
        update_wrapper (_method ,self .func )
        return _method
    @property
    def __isabstractmethod__ (self ):
        return getattr (self .func ,'__isabstractmethod__',False )
_NOT_FOUND =object ()
class cached_property :
    def __init__ (self ,func ):
        self .func =func
        self .attrname =None
        self .__doc__ =func .__doc__
        self .__module__ =func .__module__
    def __set_name__ (self ,owner ,name ):
        if self .attrname is None :
            self .attrname =name
        elif name !=self .attrname :
            raise TypeError (
            f"({self .attrname !r } and {name !r })."
            )
    def __get__ (self ,instance ,owner =None ):
        if instance is None :
            return self
        if self .attrname is None :
            raise TypeError (
            "")
        try :
            cache =instance .__dict__
        except AttributeError :
            msg =(
            f"No '__dict__' attribute on {type (instance ).__name__ !r } "
            f"instance to cache {self .attrname !r } property."
            )
            raise TypeError (msg )from None
        val =cache .get (self .attrname ,_NOT_FOUND )
        if val is _NOT_FOUND :
            val =self .func (instance )
            try :
                cache [self .attrname ]=val
            except TypeError :
                msg =(
                f"The '__dict__' attribute on {type (instance ).__name__ !r } instance "
                f"does not support item assignment for caching {self .attrname !r } property."
                )
                raise TypeError (msg )from None
        return val
    __class_getitem__ =classmethod (GenericAlias )
import collections as _collections
import dataclasses as _dataclasses
import re
import sys as _sys
import types as _types
from io import StringIO as _StringIO
__all__ =["pprint","pformat","isreadable","isrecursive","saferepr",
"","pp"]
def pprint (object ,stream =None ,indent =1 ,width =80 ,depth =None ,*,
compact =False ,sort_dicts =True ,underscore_numbers =False ):
    printer =PrettyPrinter (
    stream =stream ,indent =indent ,width =width ,depth =depth ,
    compact =compact ,sort_dicts =sort_dicts ,
    underscore_numbers =underscore_numbers )
    printer .pprint (object )
def pformat (object ,indent =1 ,width =80 ,depth =None ,*,
compact =False ,sort_dicts =True ,underscore_numbers =False ):
    return PrettyPrinter (indent =indent ,width =width ,depth =depth ,
    compact =compact ,sort_dicts =sort_dicts ,
    underscore_numbers =underscore_numbers ).pformat (object )
def pp (object ,*args ,sort_dicts =False ,**kwargs ):
    pprint (object ,*args ,sort_dicts =sort_dicts ,**kwargs )
def saferepr (object ):
    return PrettyPrinter ()._safe_repr (object ,{},None ,0 )[0 ]
def isreadable (object ):
    return PrettyPrinter ()._safe_repr (object ,{},None ,0 )[1 ]
def isrecursive (object ):
    return PrettyPrinter ()._safe_repr (object ,{},None ,0 )[2 ]
class _safe_key :
    __slots__ =['obj']
    def __init__ (self ,obj ):
        self .obj =obj
    def __lt__ (self ,other ):
        try :
            return self .obj <other .obj
        except TypeError :
            return ((str (type (self .obj )),id (self .obj ))<(str (type (other .obj )),id (other .obj )))
def _safe_tuple (t ):
    return _safe_key (t [0 ]),_safe_key (t [1 ])
class PrettyPrinter :
    def __init__ (self ,indent =1 ,width =80 ,depth =None ,stream =None ,*,
    compact =False ,sort_dicts =True ,underscore_numbers =False ):
        indent =int (indent )
        width =int (width )
        if indent <0 :
            raise ValueError ('indent must be >= 0')
        if depth is not None and depth <=0 :
            raise ValueError ('depth must be > 0')
        if not width :
            raise ValueError ('width must be != 0')
        self ._depth =depth
        self ._indent_per_level =indent
        self ._width =width
        if stream is not None :
            self ._stream =stream
        else :
            self ._stream =_sys .stdout
        self ._compact =bool (compact )
        self ._sort_dicts =sort_dicts
        self ._underscore_numbers =underscore_numbers
    def pprint (self ,object ):
        if self ._stream is not None :
            self ._format (object ,self ._stream ,0 ,0 ,{},0 )
            self ._stream .write ("\n")
    def pformat (self ,object ):
        sio =_StringIO ()
        self ._format (object ,sio ,0 ,0 ,{},0 )
        return sio .getvalue ()
    def isrecursive (self ,object ):
        return self .format (object ,{},0 ,0 )[2 ]
    def isreadable (self ,object ):
        s ,readable ,recursive =self .format (object ,{},0 ,0 )
        return readable and not recursive
    def _format (self ,object ,stream ,indent ,allowance ,context ,level ):
        objid =id (object )
        if objid in context :
            stream .write (_recursion (object ))
            self ._recursive =True
            self ._readable =False
            return
        rep =self ._repr (object ,context ,level )
        max_width =self ._width -indent -allowance
        if len (rep )>max_width :
            p =self ._dispatch .get (type (object ).__repr__ ,None )
            if p is not None :
                context [objid ]=1
                p (self ,object ,stream ,indent ,allowance ,context ,level +1 )
                del context [objid ]
                return
            elif (_dataclasses .is_dataclass (object )and
            not isinstance (object ,type )and
            object .__dataclass_params__ .repr and
            hasattr (object .__repr__ ,"__wrapped__")and
            ""in object .__repr__ .__wrapped__ .__qualname__ ):
                context [objid ]=1
                self ._pprint_dataclass (object ,stream ,indent ,allowance ,context ,level +1 )
                del context [objid ]
                return
        stream .write (rep )
    def _pprint_dataclass (self ,object ,stream ,indent ,allowance ,context ,level ):
        cls_name =object .__class__ .__name__
        indent +=len (cls_name )+1
        items =[(f .name ,getattr (object ,f .name ))for f in _dataclasses .fields (object )if f .repr ]
        stream .write (cls_name +'(')
        self ._format_namespace_items (items ,stream ,indent ,allowance ,context ,level )
        stream .write (')')
    _dispatch ={}
    def _pprint_dict (self ,object ,stream ,indent ,allowance ,context ,level ):
        write =stream .write
        write ('{')
        if self ._indent_per_level >1 :
            write ((self ._indent_per_level -1 )*' ')
        length =len (object )
        if length :
            if self ._sort_dicts :
                items =sorted (object .items (),key =_safe_tuple )
            else :
                items =object .items ()
            self ._format_dict_items (items ,stream ,indent ,allowance +1 ,
            context ,level )
        write ('}')
    _dispatch [dict .__repr__ ]=_pprint_dict
    def _pprint_ordered_dict (self ,object ,stream ,indent ,allowance ,context ,level ):
        if not len (object ):
            stream .write (repr (object ))
            return
        cls =object .__class__
        stream .write (cls .__name__ +'(')
        self ._format (list (object .items ()),stream ,
        indent +len (cls .__name__ )+1 ,allowance +1 ,
        context ,level )
        stream .write (')')
    _dispatch [_collections .OrderedDict .__repr__ ]=_pprint_ordered_dict
    def _pprint_list (self ,object ,stream ,indent ,allowance ,context ,level ):
        stream .write ('[')
        self ._format_items (object ,stream ,indent ,allowance +1 ,
        context ,level )
        stream .write (']')
    _dispatch [list .__repr__ ]=_pprint_list
    def _pprint_tuple (self ,object ,stream ,indent ,allowance ,context ,level ):
        stream .write ('(')
        endchar =',)'if len (object )==1 else ')'
        self ._format_items (object ,stream ,indent ,allowance +len (endchar ),
        context ,level )
        stream .write (endchar )
    _dispatch [tuple .__repr__ ]=_pprint_tuple
    def _pprint_set (self ,object ,stream ,indent ,allowance ,context ,level ):
        if not len (object ):
            stream .write (repr (object ))
            return
        typ =object .__class__
        if typ is set :
            stream .write ('{')
            endchar ='}'
        else :
            stream .write (typ .__name__ +'({')
            endchar ='})'
            indent +=len (typ .__name__ )+1
        object =sorted (object ,key =_safe_key )
        self ._format_items (object ,stream ,indent ,allowance +len (endchar ),
        context ,level )
        stream .write (endchar )
    _dispatch [set .__repr__ ]=_pprint_set
    _dispatch [frozenset .__repr__ ]=_pprint_set
    def _pprint_str (self ,object ,stream ,indent ,allowance ,context ,level ):
        write =stream .write
        if not len (object ):
            write (repr (object ))
            return
        chunks =[]
        lines =object .splitlines (True )
        if level ==1 :
            indent +=1
            allowance +=1
        max_width1 =max_width =self ._width -indent
        for i ,line in enumerate (lines ):
            rep =repr (line )
            if i ==len (lines )-1 :
                max_width1 -=allowance
            if len (rep )<=max_width1 :
                chunks .append (rep )
            else :
                parts =re .findall (r'\S*\s*',line )
                assert parts
                assert not parts [-1 ]
                parts .pop ()
                max_width2 =max_width
                current =''
                for j ,part in enumerate (parts ):
                    candidate =current +part
                    if j ==len (parts )-1 and i ==len (lines )-1 :
                        max_width2 -=allowance
                    if len (repr (candidate ))>max_width2 :
                        if current :
                            chunks .append (repr (current ))
                        current =part
                    else :
                        current =candidate
                if current :
                    chunks .append (repr (current ))
        if len (chunks )==1 :
            write (rep )
            return
        if level ==1 :
            write ('(')
        for i ,rep in enumerate (chunks ):
            if i >0 :
                write ('\n'+' '*indent )
            write (rep )
        if level ==1 :
            write (')')
    _dispatch [str .__repr__ ]=_pprint_str
    def _pprint_bytes (self ,object ,stream ,indent ,allowance ,context ,level ):
        write =stream .write
        if len (object )<=4 :
            write (repr (object ))
            return
        parens =level ==1
        if parens :
            indent +=1
            allowance +=1
            write ('(')
        delim =''
        for rep in _wrap_bytes_repr (object ,self ._width -indent ,allowance ):
            write (delim )
            write (rep )
            if not delim :
                delim ='\n'+' '*indent
        if parens :
            write (')')
    _dispatch [bytes .__repr__ ]=_pprint_bytes
    def _pprint_bytearray (self ,object ,stream ,indent ,allowance ,context ,level ):
        write =stream .write
        write ('bytearray(')
        self ._pprint_bytes (bytes (object ),stream ,indent +10 ,
        allowance +1 ,context ,level +1 )
        write (')')
    _dispatch [bytearray .__repr__ ]=_pprint_bytearray
    def _pprint_mappingproxy (self ,object ,stream ,indent ,allowance ,context ,level ):
        stream .write ('mappingproxy(')
        self ._format (object .copy (),stream ,indent +13 ,allowance +1 ,
        context ,level )
        stream .write (')')
    _dispatch [_types .MappingProxyType .__repr__ ]=_pprint_mappingproxy
    def _pprint_simplenamespace (self ,object ,stream ,indent ,allowance ,context ,level ):
        if type (object )is _types .SimpleNamespace :
            cls_name ='namespace'
        else :
            cls_name =object .__class__ .__name__
        indent +=len (cls_name )+1
        items =object .__dict__ .items ()
        stream .write (cls_name +'(')
        self ._format_namespace_items (items ,stream ,indent ,allowance ,context ,level )
        stream .write (')')
    _dispatch [_types .SimpleNamespace .__repr__ ]=_pprint_simplenamespace
    def _format_dict_items (self ,items ,stream ,indent ,allowance ,context ,
    level ):
        write =stream .write
        indent +=self ._indent_per_level
        delimnl =',\n'+' '*indent
        last_index =len (items )-1
        for i ,(key ,ent )in enumerate (items ):
            last =i ==last_index
            rep =self ._repr (key ,context ,level )
            write (rep )
            write (': ')
            self ._format (ent ,stream ,indent +len (rep )+2 ,
            allowance if last else 1 ,
            context ,level )
            if not last :
                write (delimnl )
    def _format_namespace_items (self ,items ,stream ,indent ,allowance ,context ,level ):
        write =stream .write
        delimnl =',\n'+' '*indent
        last_index =len (items )-1
        for i ,(key ,ent )in enumerate (items ):
            last =i ==last_index
            write (key )
            write ('=')
            if id (ent )in context :
                write ("...")
            else :
                self ._format (ent ,stream ,indent +len (key )+1 ,
                allowance if last else 1 ,
                context ,level )
            if not last :
                write (delimnl )
    def _format_items (self ,items ,stream ,indent ,allowance ,context ,level ):
        write =stream .write
        indent +=self ._indent_per_level
        if self ._indent_per_level >1 :
            write ((self ._indent_per_level -1 )*' ')
        delimnl =',\n'+' '*indent
        delim =''
        width =max_width =self ._width -indent +1
        it =iter (items )
        try :
            next_ent =next (it )
        except StopIteration :
            return
        last =False
        while not last :
            ent =next_ent
            try :
                next_ent =next (it )
            except StopIteration :
                last =True
                max_width -=allowance
                width -=allowance
            if self ._compact :
                rep =self ._repr (ent ,context ,level )
                w =len (rep )+2
                if width <w :
                    width =max_width
                    if delim :
                        delim =delimnl
                if width >=w :
                    width -=w
                    write (delim )
                    delim =', '
                    write (rep )
                    continue
            write (delim )
            delim =delimnl
            self ._format (ent ,stream ,indent ,
            allowance if last else 1 ,
            context ,level )
    def _repr (self ,object ,context ,level ):
        repr ,readable ,recursive =self .format (object ,context .copy (),
        self ._depth ,level )
        if not readable :
            self ._readable =False
        if recursive :
            self ._recursive =True
        return repr
    def format (self ,object ,context ,maxlevels ,level ):
        return self ._safe_repr (object ,context ,maxlevels ,level )
    def _pprint_default_dict (self ,object ,stream ,indent ,allowance ,context ,level ):
        if not len (object ):
            stream .write (repr (object ))
            return
        rdf =self ._repr (object .default_factory ,context ,level )
        cls =object .__class__
        indent +=len (cls .__name__ )+1
        stream .write ('%s(%s,\n%s'%(cls .__name__ ,rdf ,' '*indent ))
        self ._pprint_dict (object ,stream ,indent ,allowance +1 ,context ,level )
        stream .write (')')
    _dispatch [_collections .defaultdict .__repr__ ]=_pprint_default_dict
    def _pprint_counter (self ,object ,stream ,indent ,allowance ,context ,level ):
        if not len (object ):
            stream .write (repr (object ))
            return
        cls =object .__class__
        stream .write (cls .__name__ +'({')
        if self ._indent_per_level >1 :
            stream .write ((self ._indent_per_level -1 )*' ')
        items =object .most_common ()
        self ._format_dict_items (items ,stream ,
        indent +len (cls .__name__ )+1 ,allowance +2 ,
        context ,level )
        stream .write ('})')
    _dispatch [_collections .Counter .__repr__ ]=_pprint_counter
    def _pprint_chain_map (self ,object ,stream ,indent ,allowance ,context ,level ):
        if not len (object .maps ):
            stream .write (repr (object ))
            return
        cls =object .__class__
        stream .write (cls .__name__ +'(')
        indent +=len (cls .__name__ )+1
        for i ,m in enumerate (object .maps ):
            if i ==len (object .maps )-1 :
                self ._format (m ,stream ,indent ,allowance +1 ,context ,level )
                stream .write (')')
            else :
                self ._format (m ,stream ,indent ,1 ,context ,level )
                stream .write (',\n'+' '*indent )
    _dispatch [_collections .ChainMap .__repr__ ]=_pprint_chain_map
    def _pprint_deque (self ,object ,stream ,indent ,allowance ,context ,level ):
        if not len (object ):
            stream .write (repr (object ))
            return
        cls =object .__class__
        stream .write (cls .__name__ +'(')
        indent +=len (cls .__name__ )+1
        stream .write ('[')
        if object .maxlen is None :
            self ._format_items (object ,stream ,indent ,allowance +2 ,
            context ,level )
            stream .write ('])')
        else :
            self ._format_items (object ,stream ,indent ,2 ,
            context ,level )
            rml =self ._repr (object .maxlen ,context ,level )
            stream .write ('],\n%smaxlen=%s)'%(' '*indent ,rml ))
    _dispatch [_collections .deque .__repr__ ]=_pprint_deque
    def _pprint_user_dict (self ,object ,stream ,indent ,allowance ,context ,level ):
        self ._format (object .data ,stream ,indent ,allowance ,context ,level -1 )
    _dispatch [_collections .UserDict .__repr__ ]=_pprint_user_dict
    def _pprint_user_list (self ,object ,stream ,indent ,allowance ,context ,level ):
        self ._format (object .data ,stream ,indent ,allowance ,context ,level -1 )
    _dispatch [_collections .UserList .__repr__ ]=_pprint_user_list
    def _pprint_user_string (self ,object ,stream ,indent ,allowance ,context ,level ):
        self ._format (object .data ,stream ,indent ,allowance ,context ,level -1 )
    _dispatch [_collections .UserString .__repr__ ]=_pprint_user_string
    def _safe_repr (self ,object ,context ,maxlevels ,level ):
        typ =type (object )
        if typ in _builtin_scalars :
            return repr (object ),True ,False
        r =getattr (typ ,"__repr__",None )
        if issubclass (typ ,int )and r is int .__repr__ :
            if self ._underscore_numbers :
                return f"{object :_d}",True ,False
            else :
                return repr (object ),True ,False
        if issubclass (typ ,dict )and r is dict .__repr__ :
            if not object :
                return "{}",True ,False
            objid =id (object )
            if maxlevels and level >=maxlevels :
                return "{...}",False ,objid in context
            if objid in context :
                return _recursion (object ),False ,True
            context [objid ]=1
            readable =True
            recursive =False
            components =[]
            append =components .append
            level +=1
            if self ._sort_dicts :
                items =sorted (object .items (),key =_safe_tuple )
            else :
                items =object .items ()
            for k ,v in items :
                krepr ,kreadable ,krecur =self .format (
                k ,context ,maxlevels ,level )
                vrepr ,vreadable ,vrecur =self .format (
                v ,context ,maxlevels ,level )
                append ("%s: %s"%(krepr ,vrepr ))
                readable =readable and kreadable and vreadable
                if krecur or vrecur :
                    recursive =True
            del context [objid ]
            return "{%s}"%", ".join (components ),readable ,recursive
        if (issubclass (typ ,list )and r is list .__repr__ )or (issubclass (typ ,tuple )and r is tuple .__repr__ ):
            if issubclass (typ ,list ):
                if not object :
                    return "[]",True ,False
                format ="[%s]"
            elif len (object )==1 :
                format ="(%s,)"
            else :
                if not object :
                    return "()",True ,False
                format ="(%s)"
            objid =id (object )
            if maxlevels and level >=maxlevels :
                return format %"...",False ,objid in context
            if objid in context :
                return _recursion (object ),False ,True
            context [objid ]=1
            readable =True
            recursive =False
            components =[]
            append =components .append
            level +=1
            for o in object :
                orepr ,oreadable ,orecur =self .format (
                o ,context ,maxlevels ,level )
                append (orepr )
                if not oreadable :
                    readable =False
                if orecur :
                    recursive =True
            del context [objid ]
            return format %", ".join (components ),readable ,recursive
        rep =repr (object )
        return rep ,(rep and not rep .startswith ('<')),False
_builtin_scalars =frozenset ({str ,bytes ,bytearray ,float ,complex ,
bool ,type (None )})
def _recursion (object ):
    return ("<Recursion on %s with id=%s>"
    %(type (object ).__name__ ,id (object )))
def _wrap_bytes_repr (object ,width ,allowance ):
    current =b''
    last =len (object )//4 *4
    for i in range (0 ,len (object ),4 ):
        part =object [i :i +4 ]
        candidate =current +part
        if i ==last :
            width -=allowance
        if len (repr (candidate ))>width :
            if current :
                yield repr (current )
            current =part
        else :
            current =candidate
    if current :
        yield repr (current )
def insort_right (a ,x ,lo =0 ,hi =None ,*,key =None ):
    if key is None :
        lo =bisect_right (a ,x ,lo ,hi )
    else :
        lo =bisect_right (a ,key (x ),lo ,hi ,key =key )
    a .insert (lo ,x )
def bisect_right (a ,x ,lo =0 ,hi =None ,*,key =None ):
    if lo <0 :
        raise ValueError ('lo must be non-negative')
    if hi is None :
        hi =len (a )
    if key is None :
        while lo <hi :
            mid =(lo +hi )//2
            if x <a [mid ]:
                hi =mid
            else :
                lo =mid +1
    else :
        while lo <hi :
            mid =(lo +hi )//2
            if x <key (a [mid ]):
                hi =mid
            else :
                lo =mid +1
    return lo
def insort_left (a ,x ,lo =0 ,hi =None ,*,key =None ):
    if key is None :
        lo =bisect_left (a ,x ,lo ,hi )
    else :
        lo =bisect_left (a ,key (x ),lo ,hi ,key =key )
    a .insert (lo ,x )
def bisect_left (a ,x ,lo =0 ,hi =None ,*,key =None ):
    if lo <0 :
        raise ValueError ('lo must be non-negative')
    if hi is None :
        hi =len (a )
    if key is None :
        while lo <hi :
            mid =(lo +hi )//2
            if a [mid ]<x :
                lo =mid +1
            else :
                hi =mid
    else :
        while lo <hi :
            mid =(lo +hi )//2
            if key (a [mid ])<x :
                lo =mid +1
            else :
                hi =mid
    return lo
try :
    from _bisect import *
except ImportError :
    pass
bisect =bisect_right
insort =insort_right
import re
from json import scanner
try :
    from _json import scanstring as c_scanstring
except ImportError :
    c_scanstring =None
__all__ =['JSONDecoder','JSONDecodeError']
FLAGS =re .VERBOSE |re .MULTILINE |re .DOTALL
NaN =float ('nan')
PosInf =float ('inf')
NegInf =float ('-inf')
class JSONDecodeError (ValueError ):
    def __init__ (self ,msg ,doc ,pos ):
        lineno =doc .count ('\n',0 ,pos )+1
        colno =pos -doc .rfind ('\n',0 ,pos )
        errmsg ='%s: line %d column %d (char %d)'%(msg ,lineno ,colno ,pos )
        ValueError .__init__ (self ,errmsg )
        self .msg =msg
        self .doc =doc
        self .pos =pos
        self .lineno =lineno
        self .colno =colno
    def __reduce__ (self ):
        return self .__class__ ,(self .msg ,self .doc ,self .pos )
_CONSTANTS ={
"":NegInf ,
"":PosInf ,
"":NaN ,
}
HEXDIGITS =re .compile (r'[0-9A-Fa-f]{4}',FLAGS )
STRINGCHUNK =re .compile (r'(.*?)(["\\\x00-\x1f])',FLAGS )
BACKSLASH ={
"":'"','\\':'\\','/':'/',
"":'\b','f':'\f','n':'\n','r':'\r','t':'\t',
}
def _decode_uXXXX (s ,pos ,_m =HEXDIGITS .match ):
    esc =_m (s ,pos +1 )
    if esc is not None :
        try :
            return int (esc .group (),16 )
        except ValueError :
            pass
    msg ="Invalid \\uXXXX escape"
    raise JSONDecodeError (msg ,s ,pos )
def py_scanstring (s ,end ,strict =True ,
_b =BACKSLASH ,_m =STRINGCHUNK .match ):
    chunks =[]
    _append =chunks .append
    begin =end -1
    while 1 :
        chunk =_m (s ,end )
        if chunk is None :
            raise JSONDecodeError ("Unterminated string starting at",s ,begin )
        end =chunk .end ()
        content ,terminator =chunk .groups ()
        if content :
            _append (content )
        if terminator =='"':
            break
        elif terminator !='\\':
            if strict :
                msg ="Invalid control character {0!r} at".format (terminator )
                raise JSONDecodeError (msg ,s ,end -1 )
            else :
                _append (terminator )
                continue
        try :
            esc =s [end ]
        except IndexError :
            raise JSONDecodeError ("Unterminated string starting at",
            s ,begin )from None
        if esc !='u':
            try :
                char =_b [esc ]
            except KeyError :
                msg ="Invalid \\escape: {0!r}".format (esc )
                raise JSONDecodeError (msg ,s ,end )
            end +=1
        else :
            uni =_decode_uXXXX (s ,end )
            end +=5
            if 0xd800 <=uni <=0xdbff and s [end :end +2 ]=='\\u':
                uni2 =_decode_uXXXX (s ,end +1 )
                if 0xdc00 <=uni2 <=0xdfff :
                    uni =0x10000 +(((uni -0xd800 )<<10 )|(uni2 -0xdc00 ))
                    end +=6
            char =chr (uni )
        _append (char )
    return ''.join (chunks ),end
scanstring =c_scanstring or py_scanstring
WHITESPACE =re .compile (r'[ \t\n\r]*',FLAGS )
WHITESPACE_STR =' \t\n\r'
def JSONObject (s_and_end ,strict ,scan_once ,object_hook ,object_pairs_hook ,
memo =None ,_w =WHITESPACE .match ,_ws =WHITESPACE_STR ):
    s ,end =s_and_end
    pairs =[]
    pairs_append =pairs .append
    if memo is None :
        memo ={}
    memo_get =memo .setdefault
    nextchar =s [end :end +1 ]
    if nextchar !='"':
        if nextchar in _ws :
            end =_w (s ,end ).end ()
            nextchar =s [end :end +1 ]
        if nextchar =='}':
            if object_pairs_hook is not None :
                result =object_pairs_hook (pairs )
                return result ,end +1
            pairs ={}
            if object_hook is not None :
                pairs =object_hook (pairs )
            return pairs ,end +1
        elif nextchar !='"':
            raise JSONDecodeError (
            "",s ,end )
    end +=1
    while True :
        key ,end =scanstring (s ,end ,strict )
        key =memo_get (key ,key )
        if s [end :end +1 ]!=':':
            end =_w (s ,end ).end ()
            if s [end :end +1 ]!=':':
                raise JSONDecodeError ("Expecting ':' delimiter",s ,end )
        end +=1
        try :
            if s [end ]in _ws :
                end +=1
                if s [end ]in _ws :
                    end =_w (s ,end +1 ).end ()
        except IndexError :
            pass
        try :
            value ,end =scan_once (s ,end )
        except StopIteration as err :
            raise JSONDecodeError ("Expecting value",s ,err .value )from None
        pairs_append ((key ,value ))
        try :
            nextchar =s [end ]
            if nextchar in _ws :
                end =_w (s ,end +1 ).end ()
                nextchar =s [end ]
        except IndexError :
            nextchar =''
        end +=1
        if nextchar =='}':
            break
        elif nextchar !=',':
            raise JSONDecodeError ("Expecting ',' delimiter",s ,end -1 )
        comma_idx =end -1
        end =_w (s ,end ).end ()
        nextchar =s [end :end +1 ]
        end +=1
        if nextchar !='"':
            if nextchar =='}':
                raise JSONDecodeError ("Illegal trailing comma before end of object",s ,comma_idx )
            raise JSONDecodeError (
            "",s ,end -1 )
    if object_pairs_hook is not None :
        result =object_pairs_hook (pairs )
        return result ,end
    pairs =dict (pairs )
    if object_hook is not None :
        pairs =object_hook (pairs )
    return pairs ,end
def JSONArray (s_and_end ,scan_once ,_w =WHITESPACE .match ,_ws =WHITESPACE_STR ):
    s ,end =s_and_end
    values =[]
    nextchar =s [end :end +1 ]
    if nextchar in _ws :
        end =_w (s ,end +1 ).end ()
        nextchar =s [end :end +1 ]
    if nextchar ==']':
        return values ,end +1
    _append =values .append
    while True :
        try :
            value ,end =scan_once (s ,end )
        except StopIteration as err :
            raise JSONDecodeError ("Expecting value",s ,err .value )from None
        _append (value )
        nextchar =s [end :end +1 ]
        if nextchar in _ws :
            end =_w (s ,end +1 ).end ()
            nextchar =s [end :end +1 ]
        end +=1
        if nextchar ==']':
            break
        elif nextchar !=',':
            raise JSONDecodeError ("Expecting ',' delimiter",s ,end -1 )
        comma_idx =end -1
        try :
            if s [end ]in _ws :
                end +=1
                if s [end ]in _ws :
                    end =_w (s ,end +1 ).end ()
            nextchar =s [end :end +1 ]
        except IndexError :
            pass
        if nextchar ==']':
            raise JSONDecodeError ("Illegal trailing comma before end of array",s ,comma_idx )
    return values ,end
class JSONDecoder (object ):
    def __init__ (self ,*,object_hook =None ,parse_float =None ,
    parse_int =None ,parse_constant =None ,strict =True ,
    object_pairs_hook =None ):
        self .object_hook =object_hook
        self .parse_float =parse_float or float
        self .parse_int =parse_int or int
        self .parse_constant =parse_constant or _CONSTANTS .__getitem__
        self .strict =strict
        self .object_pairs_hook =object_pairs_hook
        self .parse_object =JSONObject
        self .parse_array =JSONArray
        self .parse_string =scanstring
        self .memo ={}
        self .scan_once =scanner .make_scanner (self )
    def decode (self ,s ,_w =WHITESPACE .match ):
        obj ,end =self .raw_decode (s ,idx =_w (s ,0 ).end ())
        end =_w (s ,end ).end ()
        if end !=len (s ):
            raise JSONDecodeError ("Extra data",s ,end )
        return obj
    def raw_decode (self ,s ,idx =0 ):
        try :
            obj ,end =self .scan_once (s ,idx )
        except StopIteration as err :
            raise JSONDecodeError ("Expecting value",s ,err .value )from None
        return obj ,end
import types
import weakref
from copyreg import dispatch_table
class Error (Exception ):
    pass
error =Error
__all__ =["Error","copy","deepcopy","replace"]
def copy (x ):
    cls =type (x )
    copier =_copy_dispatch .get (cls )
    if copier :
        return copier (x )
    if issubclass (cls ,type ):
        return _copy_immutable (x )
    copier =getattr (cls ,"__copy__",None )
    if copier is not None :
        return copier (x )
    reductor =dispatch_table .get (cls )
    if reductor is not None :
        rv =reductor (x )
    else :
        reductor =getattr (x ,"__reduce_ex__",None )
        if reductor is not None :
            rv =reductor (4 )
        else :
            reductor =getattr (x ,"__reduce__",None )
            if reductor :
                rv =reductor ()
            else :
                raise Error ("un(shallow)copyable object of type %s"%cls )
    if isinstance (rv ,str ):
        return x
    return _reconstruct (x ,None ,*rv )
_copy_dispatch =d ={}
def _copy_immutable (x ):
    return x
for t in (types .NoneType ,int ,float ,bool ,complex ,str ,tuple ,
bytes ,frozenset ,type ,range ,slice ,property ,
types .BuiltinFunctionType ,types .EllipsisType ,
types .NotImplementedType ,types .FunctionType ,types .CodeType ,
weakref .ref ):
    d [t ]=_copy_immutable
d [list ]=list .copy
d [dict ]=dict .copy
d [set ]=set .copy
d [bytearray ]=bytearray .copy
del d ,t
def deepcopy (x ,memo =None ,_nil =[]):
    d =id (x )
    if memo is None :
        memo ={}
    else :
        y =memo .get (d ,_nil )
        if y is not _nil :
            return y
    cls =type (x )
    copier =_deepcopy_dispatch .get (cls )
    if copier is not None :
        y =copier (x ,memo )
    else :
        if issubclass (cls ,type ):
            y =_deepcopy_atomic (x ,memo )
        else :
            copier =getattr (x ,"__deepcopy__",None )
            if copier is not None :
                y =copier (memo )
            else :
                reductor =dispatch_table .get (cls )
                if reductor :
                    rv =reductor (x )
                else :
                    reductor =getattr (x ,"__reduce_ex__",None )
                    if reductor is not None :
                        rv =reductor (4 )
                    else :
                        reductor =getattr (x ,"__reduce__",None )
                        if reductor :
                            rv =reductor ()
                        else :
                            raise Error (
                            ""%cls )
                if isinstance (rv ,str ):
                    y =x
                else :
                    y =_reconstruct (x ,memo ,*rv )
    if y is not x :
        memo [d ]=y
        _keep_alive (x ,memo )
    return y
_deepcopy_dispatch =d ={}
def _deepcopy_atomic (x ,memo ):
    return x
d [types .NoneType ]=_deepcopy_atomic
d [types .EllipsisType ]=_deepcopy_atomic
d [types .NotImplementedType ]=_deepcopy_atomic
d [int ]=_deepcopy_atomic
d [float ]=_deepcopy_atomic
d [bool ]=_deepcopy_atomic
d [complex ]=_deepcopy_atomic
d [bytes ]=_deepcopy_atomic
d [str ]=_deepcopy_atomic
d [types .CodeType ]=_deepcopy_atomic
d [type ]=_deepcopy_atomic
d [range ]=_deepcopy_atomic
d [types .BuiltinFunctionType ]=_deepcopy_atomic
d [types .FunctionType ]=_deepcopy_atomic
d [weakref .ref ]=_deepcopy_atomic
d [property ]=_deepcopy_atomic
def _deepcopy_list (x ,memo ,deepcopy =deepcopy ):
    y =[]
    memo [id (x )]=y
    append =y .append
    for a in x :
        append (deepcopy (a ,memo ))
    return y
d [list ]=_deepcopy_list
def _deepcopy_tuple (x ,memo ,deepcopy =deepcopy ):
    y =[deepcopy (a ,memo )for a in x ]
    try :
        return memo [id (x )]
    except KeyError :
        pass
    for k ,j in zip (x ,y ):
        if k is not j :
            y =tuple (y )
            break
    else :
        y =x
    return y
d [tuple ]=_deepcopy_tuple
def _deepcopy_dict (x ,memo ,deepcopy =deepcopy ):
    y ={}
    memo [id (x )]=y
    for key ,value in x .items ():
        y [deepcopy (key ,memo )]=deepcopy (value ,memo )
    return y
d [dict ]=_deepcopy_dict
def _deepcopy_method (x ,memo ):
    return type (x )(x .__func__ ,deepcopy (x .__self__ ,memo ))
d [types .MethodType ]=_deepcopy_method
del d
def _keep_alive (x ,memo ):
    try :
        memo [id (memo )].append (x )
    except KeyError :
        memo [id (memo )]=[x ]
def _reconstruct (x ,memo ,func ,args ,
state =None ,listiter =None ,dictiter =None ,
*,deepcopy =deepcopy ):
    deep =memo is not None
    if deep and args :
        args =(deepcopy (arg ,memo )for arg in args )
    y =func (*args )
    if deep :
        memo [id (x )]=y
    if state is not None :
        if deep :
            state =deepcopy (state ,memo )
        if hasattr (y ,'__setstate__'):
            y .__setstate__ (state )
        else :
            if isinstance (state ,tuple )and len (state )==2 :
                state ,slotstate =state
            else :
                slotstate =None
            if state is not None :
                y .__dict__ .update (state )
            if slotstate is not None :
                for key ,value in slotstate .items ():
                    setattr (y ,key ,value )
    if listiter is not None :
        if deep :
            for item in listiter :
                item =deepcopy (item ,memo )
                y .append (item )
        else :
            for item in listiter :
                y .append (item )
    if dictiter is not None :
        if deep :
            for key ,value in dictiter :
                key =deepcopy (key ,memo )
                value =deepcopy (value ,memo )
                y [key ]=value
        else :
            for key ,value in dictiter :
                y [key ]=value
    return y
del types ,weakref
def replace (obj ,/,**changes ):
    cls =obj .__class__
    func =getattr (cls ,'__replace__',None )
    if func is None :
        raise TypeError (f"replace() does not support {cls .__name__ } objects")
    return func (obj ,**changes )
__all__ =['abs','add','and_','attrgetter','call','concat','contains','countOf',
"",'eq','floordiv','ge','getitem','gt','iadd','iand',
"",'ifloordiv','ilshift','imatmul','imod','imul',
"",'indexOf','inv','invert','ior','ipow','irshift',
"",'is_not','isub','itemgetter','itruediv','ixor','le',
"",'lshift','lt','matmul','methodcaller','mod',
"",'ne','neg','not_','or_','pos','pow','rshift',
"",'sub','truediv','truth','xor']
from builtins import abs as _abs
def lt (a ,b ):
    return a <b
def le (a ,b ):
    return a <=b
def eq (a ,b ):
    return a ==b
def ne (a ,b ):
    return a !=b
def ge (a ,b ):
    return a >=b
def gt (a ,b ):
    return a >b
def not_ (a ):
    return not a
def truth (a ):
    return True if a else False
def is_ (a ,b ):
    return a is b
def is_not (a ,b ):
    return a is not b
def abs (a ):
    return _abs (a )
def add (a ,b ):
    return a +b
def and_ (a ,b ):
    return a &b
def floordiv (a ,b ):
    return a //b
def index (a ):
    return a .__index__ ()
def inv (a ):
    return ~a
invert =inv
def lshift (a ,b ):
    return a <<b
def mod (a ,b ):
    return a %b
def mul (a ,b ):
    return a *b
def matmul (a ,b ):
    return a @b
def neg (a ):
    return -a
def or_ (a ,b ):
    return a |b
def pos (a ):
    return +a
def pow (a ,b ):
    return a **b
def rshift (a ,b ):
    return a >>b
def sub (a ,b ):
    return a -b
def truediv (a ,b ):
    return a /b
def xor (a ,b ):
    return a ^b
def concat (a ,b ):
    if not hasattr (a ,'__getitem__'):
        msg ="'%s' object can't be concatenated"%type (a ).__name__
        raise TypeError (msg )
    return a +b
def contains (a ,b ):
    return b in a
def countOf (a ,b ):
    count =0
    for i in a :
        if i is b or i ==b :
            count +=1
    return count
def delitem (a ,b ):
    del a [b ]
def getitem (a ,b ):
    return a [b ]
def indexOf (a ,b ):
    for i ,j in enumerate (a ):
        if j is b or j ==b :
            return i
    else :
        raise ValueError ('sequence.index(x): x not in sequence')
def setitem (a ,b ,c ):
    a [b ]=c
def length_hint (obj ,default =0 ):
    if not isinstance (default ,int ):
        msg =("'%s' object cannot be interpreted as an integer"%
        type (default ).__name__ )
        raise TypeError (msg )
    try :
        return len (obj )
    except TypeError :
        pass
    try :
        hint =type (obj ).__length_hint__
    except AttributeError :
        return default
    try :
        val =hint (obj )
    except TypeError :
        return default
    if val is NotImplemented :
        return default
    if not isinstance (val ,int ):
        msg =('__length_hint__ must be integer, not %s'%
        type (val ).__name__ )
        raise TypeError (msg )
    if val <0 :
        msg ='__length_hint__() should return >= 0'
        raise ValueError (msg )
    return val
def call (obj ,/,*args ,**kwargs ):
    return obj (*args ,**kwargs )
class attrgetter :
    __slots__ =('_attrs','_call')
    def __init__ (self ,attr ,/,*attrs ):
        if not attrs :
            if not isinstance (attr ,str ):
                raise TypeError ('attribute name must be a string')
            self ._attrs =(attr ,)
            names =attr .split ('.')
            def func (obj ):
                for name in names :
                    obj =getattr (obj ,name )
                return obj
            self ._call =func
        else :
            self ._attrs =(attr ,)+attrs
            getters =tuple (map (attrgetter ,self ._attrs ))
            def func (obj ):
                return tuple (getter (obj )for getter in getters )
            self ._call =func
    def __call__ (self ,obj ,/):
        return self ._call (obj )
    def __repr__ (self ):
        return '%s.%s(%s)'%(self .__class__ .__module__ ,
        self .__class__ .__qualname__ ,
        "".join (map (repr ,self ._attrs )))
    def __reduce__ (self ):
        return self .__class__ ,self ._attrs
class itemgetter :
    __slots__ =('_items','_call')
    def __init__ (self ,item ,/,*items ):
        if not items :
            self ._items =(item ,)
            def func (obj ):
                return obj [item ]
            self ._call =func
        else :
            self ._items =items =(item ,)+items
            def func (obj ):
                return tuple (obj [i ]for i in items )
            self ._call =func
    def __call__ (self ,obj ,/):
        return self ._call (obj )
    def __repr__ (self ):
        return '%s.%s(%s)'%(self .__class__ .__module__ ,
        self .__class__ .__name__ ,
        "".join (map (repr ,self ._items )))
    def __reduce__ (self ):
        return self .__class__ ,self ._items
class methodcaller :
    __slots__ =('_name','_args','_kwargs')
    def __init__ (self ,name ,/,*args ,**kwargs ):
        self ._name =name
        if not isinstance (self ._name ,str ):
            raise TypeError ('method name must be a string')
        self ._args =args
        self ._kwargs =kwargs
    def __call__ (self ,obj ,/):
        return getattr (obj ,self ._name )(*self ._args ,**self ._kwargs )
    def __repr__ (self ):
        args =[repr (self ._name )]
        args .extend (map (repr ,self ._args ))
        args .extend ('%s=%r'%(k ,v )for k ,v in self ._kwargs .items ())
        return '%s.%s(%s)'%(self .__class__ .__module__ ,
        self .__class__ .__name__ ,
        "".join (args ))
    def __reduce__ (self ):
        if not self ._kwargs :
            return self .__class__ ,(self ._name ,)+self ._args
        else :
            from functools import partial
            return partial (self .__class__ ,self ._name ,**self ._kwargs ),self ._args
def iadd (a ,b ):
    a +=b
    return a
def iand (a ,b ):
    a &=b
    return a
def iconcat (a ,b ):
    if not hasattr (a ,'__getitem__'):
        msg ="'%s' object can't be concatenated"%type (a ).__name__
        raise TypeError (msg )
    a +=b
    return a
def ifloordiv (a ,b ):
    a //=b
    return a
def ilshift (a ,b ):
    a <<=b
    return a
def imod (a ,b ):
    a %=b
    return a
def imul (a ,b ):
    a *=b
    return a
def imatmul (a ,b ):
    a @=b
    return a
def ior (a ,b ):
    a |=b
    return a
def ipow (a ,b ):
    a **=b
    return a
def irshift (a ,b ):
    a >>=b
    return a
def isub (a ,b ):
    a -=b
    return a
def itruediv (a ,b ):
    a /=b
    return a
def ixor (a ,b ):
    a ^=b
    return a
try :
    from _operator import *
except ImportError :
    pass
else :
    from _operator import __doc__
__lt__ =lt
__le__ =le
__eq__ =eq
__ne__ =ne
__ge__ =ge
__gt__ =gt
__not__ =not_
__abs__ =abs
__add__ =add
__and__ =and_
__call__ =call
__floordiv__ =floordiv
__index__ =index
__inv__ =inv
__invert__ =invert
__lshift__ =lshift
__mod__ =mod
__mul__ =mul
__matmul__ =matmul
__neg__ =neg
__or__ =or_
__pos__ =pos
__pow__ =pow
__rshift__ =rshift
__sub__ =sub
__truediv__ =truediv
__xor__ =xor
__concat__ =concat
__contains__ =contains
__delitem__ =delitem
__getitem__ =getitem
__setitem__ =setitem
__iadd__ =iadd
__iand__ =iand
__iconcat__ =iconcat
__ifloordiv__ =ifloordiv
__ilshift__ =ilshift
__imod__ =imod
__imul__ =imul
__imatmul__ =imatmul
__ior__ =ior
__ipow__ =ipow
__irshift__ =irshift
__isub__ =isub
__itruediv__ =itruediv
__ixor__ =ixor
