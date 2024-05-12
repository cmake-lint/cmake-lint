# Changes

## 1.4.3

- support for python 3.12
- use ruff for linking the codebase

## 1.4.2

- add ability to override settings in $PWD/.cmakelintrc, ideally placing it in the project root folder.

## 1.4.1

- Add missing error package/stdargs category
- NOBUG: code linted

## 1.4

- Add --quiet flag to suppress "Total Errors: 0"
- Add --linelength=N flag to allow longer default lines (default remains 80)

## 1.3.4

- fix false positives in indented blocks

## 1.3.3

- fix crash on invalid `# lint_cmake: pragma` line
- fix deprecation warning with Python 3.4
- fix false positive warnings related to non-CMake quoted chunks (Issue #2)

## 1.3.2

- return error code 0, 1, 32 on error

## 1.3.1

- fix version number

## 1.3

- individual CMake files can control filters with `# lint_cmake: pragma` comment
- improved `SetFilters` function to allow spaces around the commas
- use `${XDG_CONFIG_HOME}` for the cmakelintrc file, with backwards compatible check for `~/.cmakelintrc`

## 1.2.01

- Published on pypi

## 1.2

- Moved to github
