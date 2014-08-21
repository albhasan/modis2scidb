#CHRONOS python checkFolder.py -t 60 --log INFO /dados1/scidb/toLoad/ /dados/scidb/scripts/MOD13Q1/ MOD13Q1_TEST009_20140605
import os
import sys
import argparse
import datetime
import subprocess as subp
import logging
from subprocess import check_output as qx
##################################################
# CREATE DESTINATION ARRAY
##################################################
#iquery -o dcsv -a
#set lang aql;
#DROP ARRAY MOD13Q1_TEST009_20140605;
#CREATE ARRAY MOD13Q1_TEST009_20140605 <ndvi:int16, evi:int16, quality:uint16, red:int16, nir:int16, blue:int16, mir:int16, viewza:int16, sunza:int16, relaza:int16, cdoy:int16, reli:int8> [col_id=48000:72000,502,5,row_id=38400:62400,502,5,time_id=0:9200,1,0];
#CREATE ARRAY MOD13Q1_TEST009_20140605 <ndvi:int16, evi:int16, quality:uint16, red:int16, nir:int16, blue:int16, mir:int16, viewza:int16, sunza:int16, relaza:int16, cdoy:int16, reli:int16> [col_id=48000:72000,502,5,row_id=38400:62400,502,5,time_id=0:9200,1,0];
##################################################
# GET TIME SERIES
##################################################
#iquery -o dcsv -a
#set lang aql;
#SELECT * FROM MOD13Q1_TEST009_20140605 WHERE col_id = 57600 AND row_id = 43200;
#time iquery -q "SELECT * FROM MOD13Q1_TEST009_20140605 WHERE col_id = 57600 AND row_id = 43200"

#********************************************************
# UTIL
#********************************************************
def getArrayname(aname):
	'''Return a valid SciDB array name from the input'''
	res = aname
	res = res.replace(".","_")
	res = res.replace("-","_")
	return res

def load2scidb(bfile, DESTARRAY, chunkSize1D, cmdaql, cmdafl, loadInstance):
	'''Load the binary file to SciDB'''
	#---------------
	# Script starts here
	#---------------
	cmd = ""
	try:
		tmparraylist = []
		bpath, bfilename = os.path.split(bfile)
		TMP_VALUE1D = getArrayname(bfilename)
		#---------------
		#Create the temporal 1D array for holding the data
		#---------------
		aql = "CREATE ARRAY " + TMP_VALUE1D + " <lltid:int64, ndvi:int16, evi:int16, quality:uint16, red:int16, nir:int16, blue:int16, mir:int16, viewza:int16, sunza:int16, relaza:int16, cdoy:int16, reli:int16> [k=0:*," + str(chunkSize1D) + ",0];"
		cmd = cmdaql + aql + "\""
		retcode = subp.call(cmd, shell = True)#os.system(cmd)
		tmparraylist.append(TMP_VALUE1D)
		logging.debug("Created the 1D array for the values: " + TMP_VALUE1D)
		#---------------
		#Load to 1D temporal array
		#---------------
		afl = "load(" + TMP_VALUE1D + ", '" + bfile + "', " + str(loadInstance) + ", '(int64, int16, int16, uint16, int16, int16, int16, int16, int16, int16, int16, int16, int16)', 0, shadowArray);"
		cmd = cmdafl + afl + "\""
		retcode = subp.call(cmd, shell = True)
		logging.debug("Loaded the binary file to 1D-Array using instance " + str(loadInstance))
		#---------------
		#Re-build dimension indexes and insert into the destination array
		#---------------
		afl = "insert(redimension(apply(" + TMP_VALUE1D + ",col_id, int64(lltid - floor(lltid/pow(10,11)) * pow(10,11) - floor((lltid - (floor(lltid/pow(10,11)) * pow(10,11)))/pow(10,6)) * pow(10,6)), row_id, int64(floor((lltid - (floor(lltid/pow(10,11)) * pow(10,11)))/pow(10,6))),time_id, int64(floor(lltid/pow(10,11)))), " + DESTARRAY + "), " + DESTARRAY + ");"
		cmd = cmdafl + afl + "\""
		retcode = subp.call(cmd, shell = True)
		logging.debug("Dimension indexes are built and inserted into array " + DESTARRAY)
		#---------------
		#Removes temporal arrays
		#---------------
		for an in tmparraylist:
			aql = "DROP ARRAY " + an + ";"
			cmd = cmdaql + aql + "\""
			#retcode = subp.call(cmd, shell = True)#os.system(cmd)
		logging.debug("Temporal arrays dropped")
	except subp.CalledProcessError as e:
		logging.exception("CalledProcessError: " + cmd + "\n" + str(e.message))
	except ValueError as e:
		logging.exception("ValueError: " + cmd + "\n" + str(e.message))
	except OSError as e:
		logging.exception("OSError: " + cmd + "\n" + str(e.message))
	except:
		e = sys.exc_info()[0]
		logging.exception("Unknown exception: " + cmd + "\n" + str(e.message))

#********************************************************
#WORKER
#********************************************************
def main(argv):
	t0 = datetime.datetime.now()
	parser = argparse.ArgumentParser(description = "Loads a SCIDB's binary file to SCIDB")
	parser.add_argument("binaryFilepath", help = "Path to a binary file (*.sdbbin)")
	parser.add_argument("destArray", help = "3D Array to upload the data to")
	parser.add_argument("-c", "--chunkSize1D", help = "Chunksize for the temporal 1D-array holding the loaded data", type = int, default = 262144)
	parser.add_argument("-l", "--loadInstance", help = "SciDB's instance used for uploading the data", type = int, default = -2)
	parser.add_argument("--log", help = "Log level", default = 'WARNING')
	#Get paramters
	args = parser.parse_args()
	binaryFilepath = args.binaryFilepath	
	destArray = args.destArray
	chunkSize1D = args.chunkSize1D
	loadInstance = args.loadInstance
	log = args.log
	####################################################
	# CONFIG
	####################################################
	numeric_loglevel = getattr(logging, log.upper(), None)
	if not isinstance(numeric_loglevel, int):
		raise ValueError('Invalid log level: %s' % log)
	logging.basicConfig(filename = 'log_load2scidb.log', level = numeric_loglevel, format = '%(asctime)s %(levelname)s: %(message)s')
	logging.info("load2scidb: " + str(args))
	#
	iqpath = "/opt/scidb/14.3/bin/" # Path to iquery
	cmdaql = iqpath + "iquery -nq \"" # Prefix on how to call iquery with AQL expression
	cmdafl = iqpath + "iquery -naq \"" # Prefix on how to call iquery with AFL expression
	#chunkSize1D = 262144# Chunk size of 1D arrays (load)
	#loadInstance = -2 #HACK: -2 (Load all data using the coordinator instance of the query.) is way faster than -1(Initiate the load from all instances)
	#TODO: Try named instances for loading when a multi-node SciDB is in place
	####################################################
	# SCRIPT
	####################################################
	load2scidb(binaryFilepath, destArray, chunkSize1D, cmdaql, cmdafl, loadInstance)
	t1 = datetime.datetime.now()
	tt = t1 - t0
	logging.info("Done in " + str(tt))
	
	
if __name__ == "__main__":
   main(sys.argv[1:])