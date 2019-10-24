import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = "\n" + f.read()


if __name__ == "__main__":
    setup(
        name="paragraph",
        use_scm_version=True,
        author="Othoz GmbH",
        author_email="bourguignon@othoz.com",
        description="A computation graph micro-framework providing seamless lazy and concurrent evaluation.",
        long_description=long_description,
        long_description_content_type="text/x-rst",
        keywords=["computation graph", "concurrent", "lazy"],
        url="https://github.com/Othoz/paragraph",
        project_urls={
            "Bug Tracker": "https://github.com/Othoz/paragraph/issues",
            "Documentation": "http://paragraph.readthedocs.io/en/latest/",
        },
        packages=["paragraph"],
        license="MIT",
        python_requires=">=3.6",
        setup_requires=['setuptools_scm'],
        install_requires=[
            "attrs>=18.1.0",
        ],
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: Implementation",
        ],
    )
