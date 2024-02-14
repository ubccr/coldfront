# Code Contribution

## pylint

- [pylint](https://pylint.pycqa.org/en/latest/) is a python module that tests code for style and helps enforce coding standards. The plugin pylint_django improves pylint's ability to analyse Django code.

- To run pylint with the pylint_django plugin on a python file, call pylint from the command line:
    ```
    pylint <file_path>
    ```
- pylint must either be called from the same directory as the file `setup.cfg` or you can explicitly define the config file by using the flag `--rcfile=<config_path>`.
- Note you can also run pylint on each python file in a directory by passing in the directory as <file_path>.
- For example, to run pylint on all python files in the directory `coldfront/core/statistics/` from a location other than the top level directory, run the following command:
    ```
    pylint --rcfile=/vagrant/coldfront_app/coldfront/setup.cfg coldfront/core/statistics/
    ```
- By default, output is written to stdout. To output to a file, include the `--output=<filename>` flag.
    ```
    pylint --output=<filename> <file_path>
    ```

## coverage

- [coverage](https://coverage.readthedocs.io/en/6.3.2/) is a python module that gauges the effectiveness of tests by measuring the code coverage of Python programs.

- To run coverage alongside the Django test suite, call coverage from the command line:
    ```
    coverage run manage.py test <path.to.tests>
    ```
- `<path.to.tests>` takes the normal form of calling Django tests. For example, 
to run the tests located in `coldfront/core/statistics/tests`, run the following command:
    ```
    coverage run manage.py test coldfront.core.statistics.tests
    ```
- `--source` flag limits the code measured to the code within the specified location, which can be either files or directories. To specify multiple sources, comma separate the paths.
- `--omit` flag will not measure the coverage of code within files or directories specified. Like the source flag above, comma separate multiple files or directories to omit.
- For example, the following command will ignore all migration files and
only measure code in the statistics directory.
    ```
    coverage run --omit=*/migrations/* --source=coldfront/core/statistics/ manage.py test coldfront.core.statistics.tests
    ``` 
- After successfully running, a database file `.coverage` is generated that contains the run results.
- To view the results in the command line, run:
    ```
    coverage report
    ```
- To view the report in an annotated HTML format, run:
    ```
    coverage html
    ```
- This generates the directory `htmlcov` and writes the coverage report to `htmlcov/index.html`.
    - Open `htmlcov/index.html` in a browser to view which lines of code were covered by the tests and which were not.
