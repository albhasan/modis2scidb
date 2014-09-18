modis2scidb
===========

Python scripts for uploading MODIS images to SciDB 

<h3>Pre-requisites</h3>
<ul>
<li>git.</li>
<li>Python.</li>
<li>SciDB 14.3. SciDB must be installed in the default location</li>
<li>These scripts must be installed on the SciDB coordinator instance and they must be ran using an user enabled to execute IQUERY.</li>
</ul>

<h3>Files:</h3>
<ul>	
<li><code>LICENSE</code> - License file.</li>
<li><code>README.md</code> - This file.</li>
<li><code>addHdfs2bin.py</code> - Script that export/adds an HDF file to SciDB's binary format.</li>
<li><code>checkFolder.py</code> - Script that checks a folder for SciDB's binary files.</li>
<li><code>load2scidb.py</code> - Script that loads a binary file to a SciDB database.</li>
<li><code>install_pyhdf.sh</code> - Script for installing pyhdf.</li>
<li><code>run.py</code> - It builds the path to the MODIS files and then it calls <code>addHdfs2bin.py</code>.</li>
</ul>

<h3>Instructions:</h3>
<ol>
<li>Download the scripts to the <i>script-folder</i>. Use: <code>git clone https://github.com/albhasan/modis2scidb.git</code></li>
<li>Use the <code>install_pyhdf.sh</code> script to install pyhdf on the SciDB coordinator instance. For example <code>sudo ./install_pyhdf.sh</code></li>
<li>Create a destination array in SciDB. This is the <i>dest-array</i>
	<ul>
	<li>For MOD13Q1: <code>CREATE ARRAY MOD09Q1 &lt;red:int16, nir:int16, quality:uint16&gt; [col_id=48000:72000,1014,5,row_id=38400:62400,1014,5,time_id=0:9200,1,0];</code></li>	
	<li>For MOD13Q1: <code>CREATE ARRAY MOD13Q1 &lt;ndvi:int16, evi:int16, quality:uint16, red:int16, nir:int16, blue:int16, mir:int16, viewza:int16, sunza:int16, relaza:int16, cdoy:int16, reli:int16&gt; [col_id=48000:72000,502,5,row_id=38400:62400,502,5,time_id=0:9200,1,0];</code></li>
	</ul>
</li>
<li>Create a folder accessible by SciDB. This is the <i>check-folder</i> from where data is loaded to SciDB.</li>
<li>Run <code>checkFolder.py</code> pointing to the <i>check-folder</i>; the files found here will be uploaded to SciDB. For example: <code>python checkFolder.py /home/scidb/toLoad/ /home/scidb/modis2scidb/ MOD09Q1 &</code></li>
<li>Run <code>addHdfs2bin.py</code> to export MODIS HDFs to binary files. After finishing, the file can be copied to the <i>check-folder</i>. For example: 
	<ul>
		<li><code>python addHdfs2bin.py /home/scidb/MODIS_ARC/MODIS/MOD09Q1.005/2000.02.18/MOD09Q1.A2000049.h10v08.005.2006268191328.hdf /home/scidb/MOD09Q1.A2000049.h10v08.005.2006268191328.sdbbin</code></li>
		<li><code>mv /home/scidb/MOD09Q1.A2000049.h10v08.005.2006268191328.sdbbin /home/scidb/toLoad/MOD09Q1.A2000049.h10v08.005.2006268191328.sdbbin</code></li>
	</ul>
</li>
<li><b>NOTE</b>: Alternatively, you can use <code>run.py</code> to make calls to <code>addHdfs2bin.py</code> on many HDFs.</li>
</ol>
