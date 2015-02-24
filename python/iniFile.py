# AL Apr 11,Jun13, Jul14
import os
import numpy as np

class IniError(Exception):
    pass

class iniFile(object):

    def __init__(self, settings=None, keep_includes=False):

        self.params = dict()
        self.comments = dict()
        self.readOrder = []
        self.defaults = []
        self.includes = []
        self.original_filename = None
        if isinstance(settings, basestring):
            self.readFile(settings, keep_includes)
        elif isinstance(settings, dict):
            self.params.update(settings)

    def readFile(self, filename, keep_includes=False, if_not_defined=False):
        try:
            fileincludes = []
            filedefaults = []
            self.original_filename = filename
            comments = []
            with open(filename) as textFileHandle:
                # Remove blanck lines and comment lines from the python list of lists.
                for line in textFileHandle:
                    s = line.strip()
                    if s == 'END':break
                    if s.startswith('#'):
                        comments.append(s[1:].rstrip())
                        continue
                    elif s.startswith('INCLUDE('):
                        fileincludes.append(s[s.find('(') + 1:s.rfind(')')])
                    elif s.startswith('DEFAULT('):
                        filedefaults.append(s[s.find('(') + 1:s.rfind(')')])
                    elif s != '':
                        eq = s.find('=')
                        if eq >= 0:
                            key = s[0:eq].strip()
                            if key in self.params:
                                if if_not_defined: continue
                                raise IniError('Error: duplicate key: ' + key + ' in ' + filename)
                            value = s[eq + 1:].strip()
                            self.params[key] = value
                            self.readOrder.append(key)
                            if len(comments): self.comments[key] = comments
                    if not s.startswith('#'): comments = []

            if keep_includes:
                self.includes += fileincludes
                self.defaults += filedefaults
            else:
                for ffile in fileincludes:
                    if os.path.isabs(ffile):
                        self.readFile(ffile, if_not_defined=if_not_defined)
                    else:
                        self.readFile(os.path.join(os.path.dirname(filename), ffile), if_not_defined=if_not_defined)
                for ffile in filedefaults:
                    if os.path.isabs(ffile):
                        self.readFile(ffile, if_not_defined=True)
                    else:
                        self.readFile(os.path.join(os.path.dirname(filename), ffile), if_not_defined=True)

            return self.params
        except:
            print 'Error in ' + filename
            raise

    def __str__(self):
        return "\n".join(self.fileLines())

    def saveFile(self, filename=None):
        if not filename: filename = self.original_filename
        if not filename: raise IniError('No filename for iniFile.saveFile()')
        with open(filename, 'w') as f:
            f.write(str(self))

    def fileLines(self):

        def asIniText(value):
            if type(value) == type(''): return value
            if type(value) == bool:
                return str(value)[0]
            return str(value)

        parameterLines = []
        for include in self.includes:
            parameterLines.append('INCLUDE(' + include + ')')
        for default in self.defaults:
            parameterLines.append('DEFAULT(' + default + ')')

        keys = self.params.keys()
        keys.sort()

        for key in self.readOrder:
            if key in keys:
                parameterLines.append(key + '=' + asIniText(self.params[key]));
                keys.remove(key)
        for key in keys:
            parameterLines.append(key + '=' + asIniText(self.params[key]));

        return parameterLines


    def replaceTags(self, placeholder, text):
        for key in self.params:
            self.params[key] = self.params[key].replace(placeholder, text);
        return self.params

    def delete_keys(self, keys):
        for k in keys: self.params.pop(k, None)

    def _undefined(self, name):
        raise IniError('parameter not defined: ' + name)

    def hasKey(self, name):
        return name in self.params

    def isSet(self, name, allowEmpty=False):
        return name in self.params and (allowEmpty or self.params[name] != "")

    def asType(self, name, tp, default=None, allowEmpty=False):
        if self.isSet(name, allowEmpty):
            if tp == bool:
                return self.bool(name, default)
            elif tp == list:
                return self.split(name, default)
            elif tp == np.ndarray:
                return self.ndarray(name, default)
            else:
                return tp(self.params[name])
        elif default is not None: return default
        else: self._undefined(name)

    def setAttr(self, name, instance, default=None, allowEmpty=False):
        default = getattr(instance, name, default)
        setattr(instance, name, self.asType(name, type(default), default, allowEmpty=allowEmpty))

    def bool(self, name, default=False):
        if self.isSet(name):
            s = self.params[name]
            if isinstance(s, bool): return s
            if s == 'T': return True
            elif s == 'F': return False
            raise IniError('parameter does not have valid T or F boolean value: ' + name)
        elif default is not None: return default
        else: self._undefined(name)

    def string(self, name, default=None, allowEmpty=True):
        return self.asType(name, str, default, allowEmpty=allowEmpty)

    def float(self, name, default=None):
        return self.asType(name, float, default)

    def int(self, name, default=None):
        return self.asType(name, int, default)

    def split(self, name, default=None):
        s = self.string(name, default)
        if isinstance(s, basestring): return s.split()
        else: return s

    def ndarray(self, name, default=None, tp=np.double):
        return np.array([tp(x) for x in self.split(name, default)])

    def array_int(self, name, index=1, default=None):
        return self.int(name + '(%u)' % index, default)

    def array_string(self, name, index=1, default=None):
        return self.string(name + '(%u)' % index, default)

    def array_bool(self, name, index=1, default=None):
        return self.bool(name + '(%u)' % index, default)

    def array_float(self, name, index=1, default=None):
        return self.float(name + '(%u)' % index, default)

    def relativeFileName(self, name, default=None):
        s = self.string(name, default)
        if self.original_filename is not None:
            return os.path.join(os.path.dirname(self.original_filename), s)
        return s
