Couchbase Server ==============================================================

1.-----------------------------------------------

~Download and install the latest couchbase community server

	https://www.couchbase.com/downloads

2.-----------------------------------------------

~Visit http:/127.0.0.1:89091/ (or whichever address the installer gives) to begin setup of the server

----Setup new cluster

----Create an admin account

----Accept the terms of agreement

----Configure the cluster

	Data Service quota -> 1024 MB

3.-----------------------------------------------

~Create the queue bucket

----Navigate to "buckets"

----Add Bucket

	Name -> queue
	
	Memory Quota -> 100 MB
	
	Bucket Type -> Ephemeral
	
	Replicas -> disable
	
	Ejection Method -> NRU ejection

4.-----------------------------------------------

~add default user

----Navigate to "security"

----Add user
	
	username -> default
	
	password -> default
	
	rolse -> Bucket Full Access

	

Python Client =================================================================

1.-----------------------------------------------

~Clone the github repository and checkout the latest release. 

	https://github.com/couchbase/couchbase-python-client
	
	git checkout <release>
	
	
2.-----------------------------------------------

~Download the most recent couchbase C sdk

	https://developer.couchbase.com/server/other-products/release-notes-archives/c-sdk
	
3.-----------------------------------------------

~Copy the C sdk directory (containing "bin", "include", "lib", and "share") into the couchbase python client repository (or change the "lcb_root" directory in the next step to point to its current path)

4.-----------------------------------------------

~Edit the setup.py file to point to the correct directories of the C sdk 

----Initialize "pkgdata" as a list instead of as a dictionary at line 18

    pkgdata = {}
    ->
    pkgdata = []

----Update the pkgversion

	pkgversion = '2.4.0' (or whichever version it is)

----Overwrite the code in the "else" statement, starting roughly at line 45, with the following

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


5.-----------------------------------------------

~Ensure that the proper C++ compilers are installed

----Python 3: Visual Studios C++ Build Tools

	http://landinghub.visualstudio.com/visual-cpp-build-tools
	
----Python 2: Visual C++ Compiler for Python 2.7

	https://www.microsoft.com/en-us/download/details.aspx?id=44266
	
6.-----------------------------------------------

~Activate the python environment of choice, change directories to the couchbase python client repository, and run the installer. Git must be callable from the command line for the installation to work (setup.py calls an automatic version finding function that uses git).

    activate <python environment> # activation syntax if using an anaconda distribution
    cd <coubase python client repository>
    python setup.py install

	
7.-----------------------------------------------

~After setup is complete, the installed package should be located in the "site-packages" directory, <Python_Directory>\Lib\site-packages\couchbase-<version info>.egg
	
8.-----------------------------------------------

~If the package needs to be reinstalled with an altered setup.py file, use the setup.py clean function to clear the cache from the old setup.py file

    python setup.py clean --all
    python setup.py install

