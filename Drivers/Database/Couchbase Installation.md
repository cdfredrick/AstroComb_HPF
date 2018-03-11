1.----------------------------

~Clone the couchbase python client repository with git

	git clone https://github.com/couchbase/couchbase-python-client
	
2.-----------------------------

~Checkout the most recent stable release

	git checkout <release id>
	
3.----------------------------

~Download the most recent couchbase C sdk

	https://developer.couchbase.com/server/other-products/release-notes-archives/c-sdk
	
4.----------------------------

~Copy the C sdk directory (containing "bin", "include", "lib", and "share") into the couchbase python client repository (or change the "lcb_root" directory in the next step to point its current path)

5.----------------------------

~Edit the setup.py file to point to the correct directories of the C sdk 

----Initialize "pkgdata" as a list instead of as a dictionary at line 18

    pkgdata = {}
    ->
    pkgdata = []

----Overwrite the code in the "else" statement starting roughly at line 45

    lcb_root = os.path.join(os.getcwd(),'<C sdk directory>')

    extoptions['libraries'] = ['libcouchbase']
    extoptions['library_dirs'] = [os.path.join(lcb_root, 'lib')]
    extoptions['include_dirs'] = [os.path.join(lcb_root, 'include')]
    extoptions['define_macros'] = [('_CRT_SECURE_NO_WARNINGS', 1)]
    pkgdata = [('couchbase', [os.path.join(lcb_root, 'bin', 'libcouchbase.dll')])]


----Replace the "package_data" keyword with "data_files" within the setup call (roughly line 133)

    package_data = pkgdata,
    ->
    data_files = pkgdata,


6.----------------------------
~Ensure that the proper C++ compilers are installed

----Python 3: Visual Studios C++ Build Tools

	http://landinghub.visualstudio.com/visual-cpp-build-tools
	
----Python 2: Visual C++ Compiler for Python 2.7

	https://www.microsoft.com/en-us/download/details.aspx?id=44266
	
7.----------------------------

~Activate the python environment of choice, change directories to the couchbase python client repository, and run the installer.

    activate <python environment> # activation syntax if using an anaconda distribution
    cd <coubase python client repository>
    python setup.py install

	
8.----------------------------

~After setup is complete, the installed package should be located in the "site-packages" directory, <Python_Directory>\Lib\site-packages\couchbase-<version info>.egg
	
9.----------------------------

~If the package needs to be reinstalled with an altered setup.py file, use the setup.py clean function to clear the cache from the old setup.py file

    python setup.py clean --all
    python setup.py install

