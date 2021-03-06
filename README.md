# google-adwords-dumper

google-adwords-dumper is a program to fetch basic data of an adwords
account and some relevant performance reports of the account. It also
fetches the data of child accounts if the given account is a master
account.

Copyright (C) 2016 Adrin Jalali

This program was developed originally at [Mister Spex GmbH](https://corporate.misterspex.com/en/)
and then released under GPLv3+ with their permission.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

## Prerequisite
This program is written and tested under python3.4+, Debian and ArchLinux.

Dependencies include: `sqlalchemy`, `googleads`, `pyodbc`

Recommended environment is a python virtual environment:

    virtualenv --python python3 venv
    source venv/bin/activate
    pip install sqlalchemy googleads pyodbc

You need to set two set configuration in two configuration files before 
running the program. You should store required parameters to connect to google
adwords in [`googleads.yaml`](https://github.com/adrinjalali/google-adwords-dumper/blob/master/googleads.yaml) in you home directory. An example of the file is provided
in this repository. You can follow the tutorial available [here](https://developers.google.com/adwords/api/docs/guides/first-api-call) to acquire those required values.

You also need to have `connectionstrings.cfg` in your home folder with the following lines in it. The program assumes the server is a MSSQL server for now.


    [adwords]
    connection-string =mssql+pyodbc://username:password@mssqlserver.fqdn.address:1433/databasename?driver=FreeTDS;tds_version=7.2

## Execution
you can run the program through `main.py` script. Arguments include:

`--start-date`: the start date of performance reports to be fetched.

`--end-date`: the end date of performance reports to be fetched.

`--create-tables`: this will create all destination tables in the database if they don't already exist.

`-v[vvvvv]`: verbosity level. `-vvvvv` is DEBUG level. `-vvvv` is recommended.

If `start-date` and `end-date` arguments are not given to the program, the program looks at the largest date for each performance report, and it downloads the data from the day after that largest date until yesterday. If the number of returned records by google differ from the number of records for the largest date in the database, the program deletes those records and tries fetching the data from google starting that date. The program does not try to check completeness of the data for dates before that date.

It is recommended to run the program leaving `start-date` and `end-date` empty. The program does not try to delete existing records in the database for given dates and it may cause duplicate records. You need to handle it manually if you intend to re-fetch data for certain dates.

## Contact/Questions
Please open an issue [here](https://github.com/adrinjalali/google-adwords-dumper/issues) for any questions or bugs you find, inccluding questions on documentation and usage of the program.
