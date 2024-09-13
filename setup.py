from setuptools import setup

setup(
    name='3gs-scraper',
    version='0.1.0',
    author='Sean Becker',
    author_email='sean.becker15@gmail.com',
    packages=['scraper'],
    license='LICENSE.txt',
    install_requires=[
        "selenium == 4.7.2",
        "python-dotenv == 0.21.0",
    ],
)
