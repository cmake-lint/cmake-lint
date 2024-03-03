"""
Copyright 2009 Richard Quirk

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this file except in compliance with the License. You may obtain a copy of
the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""
from __future__ import print_function
import sys
import re
import os
import getopt
import cmakelint.__version__


_RE_COMMAND = re.compile(r'^\s*(\w+)(\s*)\(', re.VERBOSE)
_RE_COMMAND_START_SPACES = re.compile(r'^\s*\w+\s*\((\s*)', re.VERBOSE)
_RE_COMMAND_END_SPACES = re.compile(r'(\s*)\)', re.VERBOSE)
_RE_LOGIC_CHECK = re.compile(r'(\w+)\s*\(\s*\S+[^)]+\)', re.VERBOSE)
_RE_COMMAND_ARG = re.compile(r'(\w+)', re.VERBOSE)
_logic_commands = """
else
endforeach
endfunction
endif
endmacro
endwhile
""".split()
_USAGE = """
Syntax: cmakelint.py [--version] [--config=file] [--filter=-x,+y] [--spaces=N]
                     [--quiet] [--linelength=digits]
        <file> [file] ...
    filter=-x,+y,...
      Specify a comma separated list of filters to apply

    spaces=N
      Indentation should be a multiple of N spaces

    config=file
      Use the given file for configuration. By default the file
      $PWD/.cmakelintrc, ~/.config/cmakelintrc, $XDG_CONFIG_DIR/cmakelintrc or
      ~/.cmakelintrc is used if it exists. Use the value "None" to use no
      configuration file (./None for a file called literally None) Only the
      option "filter=" is currently supported in this file.

    quiet makes output quiet unless errors occurs
      Mainly used by automation tools when parsing huge amount of files.
      In those cases actual error might get lost in the pile of other stats
      prints.

      This argument is also handy for build system integration, so it's
      possible to add automated lint target to a project and invoke it
      via build system and have no pollution of terminals or IDE.

    linelength=digits
      This is the allowed line length for the project. The default value is
      80 characters.

      Examples:
        --linelength=120

    version
      Show the version number and end
"""
_ERROR_CATEGORIES = """\
        convention/filename
        linelength
        package/consistency
        package/stdargs
        readability/logic
        readability/mixedcase
        readability/wonkycase
        syntax
        whitespace/eol
        whitespace/extra
        whitespace/indent
        whitespace/mismatch
        whitespace/newline
        whitespace/tabs
"""
_DEFAULT_FILENAME = 'CMakeLists.txt'

def DefaultRC():
    """
    Check current working directory and XDG_CONFIG_DIR before ~/.cmakelintrc
    """
    cwdfile = os.path.join(os.getcwd(), '.cmakelintrc')
    if os.path.exists(cwdfile):
        return cwdfile
    xdg = os.path.join(os.path.expanduser('~'), '.config')
    if 'XDG_CONFIG_DIR' in os.environ:
        xdg = os.environ['XDG_CONFIG_DIR']
    xdgfile = os.path.join(xdg, 'cmakelintrc')
    if os.path.exists(xdgfile):
        return xdgfile
    return os.path.join(os.path.expanduser('~'), '.cmakelintrc')

_DEFAULT_CMAKELINTRC = DefaultRC()

class _CMakeLintState(object):
    def __init__(self):
        self.filters = []
        self.config = 0
        self.errors = 0
        self.spaces = 2
        self.linelength = 80
        self.allowed_categories = _ERROR_CATEGORIES.split()
        self.quiet = False

    def SetFilters(self, filters):
        if not filters:
            return
        assert isinstance(self.filters, list)
        if isinstance(filters, list):
            self.filters.extend(filters)
        elif isinstance(filters, str):
            self.filters.extend([f.strip() for f in filters.split(',') if f])
        else:
            raise ValueError('Filters should be a list or a comma separated string')
        for f in self.filters:
            if f.startswith('-') or f.startswith('+'):
                allowed = False
                for c in self.allowed_categories:
                    if c.startswith(f[1:]):
                        allowed = True
                if not allowed:
                    raise ValueError('Filter not allowed: %s'%f)
            else:
                raise ValueError('Filter should start with - or +')

    def SetSpaces(self, spaces):
        self.spaces = int(spaces.strip())

    def SetQuiet(self, quiet):
        self.quiet = quiet

    def SetLineLength(self, linelength):
        self.linelength = int(linelength)

class _CMakePackageState(object):
    def __init__(self):
        self.sets = []
        self.have_included_stdargs = False
        self.have_used_stdargs = False

    def Check(self, filename, linenumber, clean_lines, errors):
        pass

    def _GetExpected(self, filename):
        package = os.path.basename(filename)
        package = re.sub(r'^Find(.*)\.cmake', lambda m: m.group(1), package)
        return package.upper()

    def Done(self, filename, errors):
        try:
            if not IsFindPackage(filename):
                return
            if self.have_included_stdargs and self.have_used_stdargs:
                return
            if not self.have_included_stdargs:
                errors(
                    filename,
                    0,
                    'package/consistency',
                    'Package should include FindPackageHandleStandardArgs')
            if not self.have_used_stdargs:
                errors(
                    filename,
                    0,
                    'package/consistency',
                    'Package should use FIND_PACKAGE_HANDLE_STANDARD_ARGS')
        finally:
            self.have_used_stdargs = False
            self.have_included_stdargs = False

    def HaveUsedStandardArgs(self, filename, linenumber, var, errors):
        expected = self._GetExpected(filename)
        self.have_used_stdargs = True
        if expected != var:
            errors(
                filename,
                linenumber,
                'package/stdargs',
                'Weird variable passed to std args, should be ' +
                expected + ' not ' + var)

    def HaveIncluded(self, var):
        if var == 'FindPackageHandleStandardArgs':
            self.have_included_stdargs = True

    def Set(self, var):
        self.sets.append(var)

_lint_state = _CMakeLintState()
_package_state = _CMakePackageState()

def CleanComments(line, quote=False):
    """
    quote means 'was in a quote starting this line' so that
    quoted lines can be eaten/removed.
    """
    if line.find('#') == -1 and line.find('"') == -1:
        if quote:
            return '', quote
        else:
            return line, quote
    # else have to check for comment
    prior = []
    prev = ''
    for char in line:
        try:
            if char == '"':
                if prev != '\\':
                    quote = not quote
                    prior.append(char)
                continue
            elif char == '#' and not quote:
                break
            if not quote:
                prior.append(char)
        finally:
            prev = char

    # rstrip removes trailing space between end of command and the comment # start

    return ''.join(prior).rstrip(), quote

class CleansedLines(object):
    def __init__(self, lines):
        self.have_seen_uppercase = None
        self.raw_lines = lines
        self.lines = []
        quote = False
        for line in lines:
            cleaned, quote = CleanComments(line, quote)
            self.lines.append(cleaned)

    def LineNumbers(self):
        return range(0, len(self.lines))

def ShouldPrintError(category):
    should_print = True
    for f in _lint_state.filters:
        if f.startswith('-') and category.startswith(f[1:]):
            should_print = False
        elif f.startswith('+') and category.startswith(f[1:]):
            should_print = True
    return should_print

def Error(filename, linenumber, category, message):
    if ShouldPrintError(category):
        _lint_state.errors += 1
        print('%s:%d: %s [%s]' % (filename, linenumber, message, category))

def CheckLineLength(filename, linenumber, clean_lines, errors):
    """
    Check for lines longer than the recommended length
    """
    line = clean_lines.raw_lines[linenumber]
    if len(line) > _lint_state.linelength:
        return errors(
                filename,
                linenumber,
                'linelength',
                'Lines should be <= %d characters long' %
                    (_lint_state.linelength))

def ContainsCommand(line):
    return _RE_COMMAND.match(line)

def GetCommand(line):
    match = _RE_COMMAND.match(line)
    if match:
        return match.group(1)
    return ''

def IsCommandMixedCase(command):
    lower = command.lower()
    upper = command.upper()
    return not (command == lower or command == upper)

def IsCommandUpperCase(command):
    upper = command.upper()
    return command == upper

def CheckUpperLowerCase(filename, linenumber, clean_lines, errors):
    """
    Check that commands are either lower case or upper case, but not both
    """
    line = clean_lines.lines[linenumber]
    if ContainsCommand(line):
        command = GetCommand(line)
        if IsCommandMixedCase(command):
            return errors(
                    filename,
                    linenumber,
                    'readability/wonkycase',
                    'Do not use mixed case commands')
        if clean_lines.have_seen_uppercase is None:
            clean_lines.have_seen_uppercase = IsCommandUpperCase(command)
        else:
            is_upper = IsCommandUpperCase(command)
            if is_upper != clean_lines.have_seen_uppercase:
                return errors(
                        filename,
                        linenumber,
                        'readability/mixedcase',
                        'Do not mix upper and lower case commands')

def GetInitialSpaces(line):
    initial_spaces = 0
    while initial_spaces < len(line) and line[initial_spaces] == ' ':
        initial_spaces += 1
    return initial_spaces

def CheckCommandSpaces(filename, linenumber, clean_lines, errors):
    """
    No extra spaces between command and parenthesis
    """
    line = clean_lines.lines[linenumber]
    match = ContainsCommand(line)
    if match and len(match.group(2)):
        errors(filename, linenumber, 'whitespace/extra',
                "Extra spaces between '%s' and its ()"%(match.group(1)))
    if match:
        spaces_after_open = len(_RE_COMMAND_START_SPACES.match(line).group(1))
        initial_spaces = GetInitialSpaces(line)
        initial_linenumber = linenumber
        end = None
        while True:
            line = clean_lines.lines[linenumber]
            end = _RE_COMMAND_END_SPACES.search(line)
            if end:
                break
            linenumber += 1
            if linenumber >= len(clean_lines.lines):
                break
        if linenumber == len(clean_lines.lines) and not end:
            errors(filename, initial_linenumber, 'syntax',
                    'Unable to find the end of this command')
        if end:
            spaces_before_end = len(end.group(1))
            initial_spaces = GetInitialSpaces(line)
            if initial_linenumber != linenumber and spaces_before_end >= initial_spaces:
                spaces_before_end -= initial_spaces

            if spaces_after_open != spaces_before_end:
                errors(filename, initial_linenumber, 'whitespace/mismatch',
                        'Mismatching spaces inside () after command')

def CheckRepeatLogic(filename, linenumber, clean_lines, errors):
    """
    Check for logic inside else, endif etc
    """
    line = clean_lines.lines[linenumber]
    for cmd in _logic_commands:
        if re.search(r'\b%s\b'%cmd, line.lower()):
            m = _RE_LOGIC_CHECK.search(line)
            if m:
                errors(filename, linenumber, 'readability/logic',
                        'Expression repeated inside %s; '
                        'better to use only %s()'%(cmd, m.group(1)))
            break

def CheckIndent(filename, linenumber, clean_lines, errors):
    line = clean_lines.raw_lines[linenumber]
    initial_spaces = GetInitialSpaces(line)
    remainder = initial_spaces % _lint_state.spaces
    if remainder != 0:
        errors(filename, linenumber, 'whitespace/indent',
                'Weird indentation; use %d spaces'%(_lint_state.spaces))

def CheckStyle(filename, linenumber, clean_lines, errors):
    """
    Check style issues. These are:
    No extra spaces between command and parenthesis
    Matching spaces between parenthesis and arguments
    No repeated logic in else(), endif(), endmacro()
    """
    CheckIndent(filename, linenumber, clean_lines, errors)
    CheckCommandSpaces(filename, linenumber, clean_lines, errors)
    line = clean_lines.raw_lines[linenumber]
    if line.find('\t') != -1:
        errors(filename, linenumber, 'whitespace/tabs', 'Tab found; please use spaces')

    if line and line[-1].isspace():
        errors(filename, linenumber, 'whitespace/eol', 'Line ends in whitespace')

    CheckRepeatLogic(filename, linenumber, clean_lines, errors)

def CheckFileName(filename, errors):
    name_match = re.match(r'Find(.*)\.cmake', os.path.basename(filename))
    if name_match:
        package = name_match.group(1)
        if not package.isupper():
            errors(filename, 0, 'convention/filename',
                    'Find modules should use uppercase names; '
                    'consider using Find' + package.upper() + '.cmake')
    else:
        if filename.lower() == 'cmakelists.txt' and filename != 'CMakeLists.txt':
            errors(filename, 0, 'convention/filename',
                    'File should be called CMakeLists.txt')

def IsFindPackage(filename):
    return os.path.basename(filename).startswith('Find') and filename.endswith('.cmake')

def GetCommandArgument(linenumber, clean_lines):
    line = clean_lines.lines[linenumber]
    skip = GetCommand(line)
    while True:
        line = clean_lines.lines[linenumber]
        m = _RE_COMMAND_ARG.finditer(line)
        for i in m:
            if i.group(1) == skip:
                continue
            return i.group(1)
        linenumber += 1
    return ''

def CheckFindPackage(filename, linenumber, clean_lines, errors):
    cmd = GetCommand(clean_lines.lines[linenumber])
    if cmd:
        if cmd.lower() == 'include':
            var_name = GetCommandArgument(linenumber, clean_lines)
            _package_state.HaveIncluded(var_name)
        elif cmd.lower() == 'find_package_handle_standard_args':
            var_name = GetCommandArgument(linenumber, clean_lines)
            _package_state.HaveUsedStandardArgs(filename, linenumber, var_name, errors)

def ProcessLine(filename, linenumber, clean_lines, errors):
    """
    Arguments:
      filename    the name of the file
      linenumber  the line number index
      clean_lines CleansedLines instance
      errors      the error handling function
    """
    CheckLintPragma(filename, linenumber, clean_lines.raw_lines[linenumber], errors)
    CheckLineLength(filename, linenumber, clean_lines, errors)
    CheckUpperLowerCase(filename, linenumber, clean_lines, errors)
    CheckStyle(filename, linenumber, clean_lines, errors)
    if IsFindPackage(filename):
        CheckFindPackage(filename, linenumber, clean_lines, errors)

def IsValidFile(filename):
    return filename.endswith('.cmake') or os.path.basename(filename).lower() == 'cmakelists.txt'

def ProcessFile(filename):
    # Store and then restore the filters to prevent pragmas in the file from persisting.
    original_filters = list(_lint_state.filters)
    try:
        return _ProcessFile(filename)
    finally:
        _lint_state.filters = original_filters

def CheckLintPragma(filename, linenumber, line, errors=None):
    # Check this line to see if it is a lint_cmake pragma
    linter_pragma_start = '# lint_cmake: '
    if line.startswith(linter_pragma_start):
        try:
            _lint_state.SetFilters(line[len(linter_pragma_start):])
        except ValueError as ex:
            if errors:
                errors(filename, linenumber, 'syntax', str(ex))
        except Exception:
            print("Exception occurred while processing '{0}:{1}':"
                  .format(filename, linenumber))

def _ProcessFile(filename):
    lines = ['# Lines start at 1']
    have_cr = False
    if not IsValidFile(filename):
        print('Ignoring file: ' + filename)
        return
    global _package_state
    _package_state = _CMakePackageState()
    for line in open(filename).readlines():
        line = line.rstrip('\n')
        if line.endswith('\r'):
            have_cr = True
            line = line.rstrip('\r')
        lines.append(line)
        CheckLintPragma(filename, len(lines) - 1, line)
    lines.append('# Lines end here')
    # Check file name after reading lines incase of a # lint_cmake: pragma
    CheckFileName(filename, Error)
    if have_cr and os.linesep != '\r\n':
        Error(filename, 0, 'whitespace/newline', 'Unexpected carriage return found; '
                'better to use only \\n')
    clean_lines = CleansedLines(lines)
    for line in clean_lines.LineNumbers():
        ProcessLine(filename, line, clean_lines, Error)
    _package_state.Done(filename, Error)

def PrintVersion():
    sys.stderr.write("cmakelint %s\n" % cmakelint.__version__.VERSION)
    sys.exit(0)

def PrintUsage(message):
    sys.stderr.write(_USAGE)
    if message:
        sys.stderr.write('FATAL ERROR: %s\n' % message)
    sys.exit(32)

def PrintCategories():
    sys.stderr.write(_ERROR_CATEGORIES)
    sys.exit(0)

def ParseOptionFile(contents, ignore_space):
    filters = None
    spaces = None
    linelength = None
    for line in contents:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('filter='):
            filters = line.replace('filter=', '')
        if line.startswith('spaces='):
            spaces = line.replace('spaces=', '')
        if line == 'quiet':
            _lint_state.SetQuiet(True)
        if line.startswith('linelength='):
            linelength = line.replace('linelength=', '')
    _lint_state.SetFilters(filters)
    if spaces and not ignore_space:
        _lint_state.SetSpaces(spaces)
    if linelength is not None:
        _lint_state.SetLineLength(linelength)


# See https://stackoverflow.com/a/30299145 - fixes deprecation warning in py 3.4+
if sys.version_info[0] == 2:
    def OpenTextFile(filename):
        return open(filename, 'rU')
else:
    def OpenTextFile(filename):
        return open(filename, 'r', newline=None)

def ParseArgs(argv):
    try:
        (opts, filenames) = getopt.getopt(argv, '',
                ['help', 'filter=', 'config=', 'spaces=', 'linelength=',
                 'quiet', 'version'])
    except getopt.GetoptError:
        PrintUsage('Invalid Arguments')
    filters = ""
    _lint_state.config = _DEFAULT_CMAKELINTRC
    ignore_space = False
    for (opt, val) in opts:
        if opt == '--version':
            PrintVersion()
        elif opt == '--help':
            PrintUsage(None)
        elif opt == '--filter':
            filters = val
            if not filters:
                PrintCategories()
        elif opt == '--config':
            _lint_state.config = val
            if _lint_state.config == 'None':
                _lint_state.config = None
        elif opt == '--spaces':
            try:
                _lint_state.SetSpaces(val)
                ignore_space = True
            except Exception:
                PrintUsage('spaces expects an integer value')
        elif opt == '--quiet':
            _lint_state.quiet = True
        elif opt == '--linelength':
            try:
                _lint_state.SetLineLength(val)
            except Exception:
                PrintUsage('line length expects an integer value')
    try:
        if _lint_state.config:
            try:
                ParseOptionFile(OpenTextFile(_lint_state.config).readlines(), ignore_space)
            except IOError:
                pass
        _lint_state.SetFilters(filters)
    except ValueError as ex:
        PrintUsage(str(ex))

    if not filenames:
        if os.path.isfile(_DEFAULT_FILENAME):
            filenames = [_DEFAULT_FILENAME]
        else:
            PrintUsage('No files were specified!')
    return filenames

def main():
    files = ParseArgs(sys.argv[1:])

    for filename in files:
        ProcessFile(filename)
    if _lint_state.errors > 0 or not _lint_state.quiet:
        sys.stderr.write("Total Errors: %d\n" % _lint_state.errors)
    if _lint_state.errors > 0:
        return 1
    else:
        return 0
