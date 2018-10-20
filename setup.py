from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='rolog',
      version='1.0.0',
      description='Async friendly logging classes for Python 3',
      long_description=readme(),
      long_description_content_type='text/markdown',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3',
          'Operating System :: OS Independent'
      ],
      url='https://github.com/RobertoPrevato/rolog',
      author='RobertoPrevato',
      author_email='roberto.prevato@gmail.com',
      keywords='logging async await',
      license='MIT',
      packages=['rolog', 'rolog.targets'],
      install_requires=[],
      include_package_data=True,
      zip_safe=False)
