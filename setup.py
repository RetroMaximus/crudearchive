from setuptools import setup, find_packages
# original line >>>>       'crudearch-manager=crudearch.manager:run_gui'
setup(
    name="crudearch",
    version="1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [

            'crudearch-manager=crudearch/manager:run_gui'
        ]
    }
)
