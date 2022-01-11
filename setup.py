import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="titan-zeus",
    version="1.1.0",
    author="AlexCLeduc",
    # author_email="author@example.com",
    # description="A small example package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TBS-EACPD/zeus",
    packages=[
        # find_packages() also includes extraneous stuff, like testing and django_sample
        package
        for package in setuptools.find_packages()
        if package.startswith("zeus")
    ],
    package_data={"": ["**/*.text.yaml"]},
    include_package_data=True,
    install_requires=[],
    tests_require=["django"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
