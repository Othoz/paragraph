from setuptools import find_packages
from setuptools import setup


if __name__ == "__main__":
    setup(
        name="othoz-paragraph",

        # Use the default-setting from setuptools_scm to generate a version number from Git tag etc., see
        # https://github.com/pypa/setuptools_scm
        use_scm_version=True,
        setup_requires=['setuptools_scm'],

        author="Othoz GmbH",
        include_package_data=False,
        packages=find_packages(),
        namespace_packages=[
            "othoz"
        ],
        description="A computation graph micro-framework providing seamless lazy and parallel evaluation.",
        # By default setuptools tries to detect automagically if a package can be zipped. However,
        # a zipped package does seem to not work well with conda - so we force setuptools to not
        # zip the package
        zip_safe=False
    )
