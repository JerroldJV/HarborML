from setuptools import setup, find_packages

setup(
    name='harborml',
    version='0.1',
    packages=find_packages(exclude=['tests*']),
    license='GPLv3',
    description='Framework for building, training, and deploying machine learning and AI solutions via containers',
    long_description=open('README.md').read(),
    url='https://github.com/JerroldJV/HarborML',
    author='Jerrold Vincent',
    author_email='JerroldJVincent@gmail.com',
    package_data={'harborml': ['static/*', 'static/flask/*']},
    install_requires=[
        'click',
        'docker'
    ],
)