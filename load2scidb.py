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
	if (is_number(aname[0]) == True):
		res = 'A' + res
	return res

def is_number(s):
	'''Test if the given string is numeric - http://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-in-python
	'''
	try:
		float(s)
		return True
	except ValueError:
		return False
	
	
def processDatatypes(schema):
	'''Return the data types from each field in an array schema'''
	datatypes = []
	for s in schema.split(','):
		ss = s.strip()
		datatypes.append(ss[ss.index(':') + 1:len(ss)])
	return ', '.join(datatypes)

		
def load2scidb(bfile, DESTARRAY, flatArrayAQL, cmdaql, cmdafl, loadInstance):
	'''Load the binary file to SciDB'''
	#---------------
	# Script starts here
	#---------------
	cmd = ""
	try:
		logging.info("Loading: " + bfile)
		tmparraylist = []
		TMP_VALUE1D = flatArrayAQL.split(' ')[2]
		schema = flatArrayAQL[flatArrayAQL.index('<') + 1:flatArrayAQL.index('>')]
		#Create the temporal 1D array for holding the data
		cmd = flatArrayAQL + "; "
		tmparraylist.append(TMP_VALUE1D)
		#Load to 1D temporal array
		afl = "load(" + TMP_VALUE1D + ", '" + bfile + "', " + str(loadInstance) + ", '(" + processDatatypes(schema) + ")', 0, shadowArray);"
		cmd = cmd + afl + "; "
		#Re-build dimension indexes and insert into the destination array
		afl = "insert(redimension(apply(" + TMP_VALUE1D + ",col_id, int64(lltid - floor(lltid/pow(10,11)) * pow(10,11) - floor((lltid - (floor(lltid/pow(10,11)) * pow(10,11)))/pow(10,6)) * pow(10,6)), row_id, int64(floor((lltid - (floor(lltid/pow(10,11)) * pow(10,11)))/pow(10,6))),time_id, int64(floor(lltid/pow(10,11)))), " + DESTARRAY + "), " + DESTARRAY + ");"
		cmd = cmd + afl + "; "
		#Remove temporal arrays
		for an in tmparraylist:
			afl = "remove(" + an + ");"
			cmd = cmd + afl + "; "
		cmd = cmdafl + cmd + "\""
		logging.debug("Query: " + cmd)
		retcode = subp.call(cmd, shell = True)
		logging.info("Load completed: " + bfile)
	except subp.CalledProcessError as e:
		logging.exception("CalledProcessError: " + cmd + "\n" + str(e.message))
	except ValueError as e:
		logging.exception("ValueError: " + cmd + "\n" + str(e.message))
	except OSError as e:
		logging.exception("OSError: " + cmd + "\n" + str(e.message))
	except:
		e = sys.exc_info()[0]
		logging.exception("Unknown exception: " + cmd + "\n" + str(e.message))		


def buildCmd(bfile, DESTARRAY, flatArrayAQL, cmdaql, cmdafl, loadInstance):
	'''DEPRECATED: Build the commands for loading the binary file to SciDB'''
	cmd = ""
	tmparraylist = []
	TMP_VALUE1D = flatArrayAQL.split(' ')[2]
	schema = flatArrayAQL[flatArrayAQL.index('<') + 1:flatArrayAQL.index('>')]
	#Create the temporal 1D array for holding the data
	cmd = flatArrayAQL + " && "
	tmparraylist.append(TMP_VALUE1D)
	#Load to 1D temporal array
	afl = "load(" + TMP_VALUE1D + ", '" + bfile + "', " + str(loadInstance) + ", '(" + processDatatypes(schema) + ")', 0, shadowArray);"
	cmd = cmd + afl + " && "
	#Re-build dimension indexes and insert into the destination array
	afl = "insert(redimension(apply(" + TMP_VALUE1D + ",col_id, int64(lltid - floor(lltid/pow(10,11)) * pow(10,11) - floor((lltid - (floor(lltid/pow(10,11)) * pow(10,11)))/pow(10,6)) * pow(10,6)), row_id, int64(floor((lltid - (floor(lltid/pow(10,11)) * pow(10,11)))/pow(10,6))),time_id, int64(floor(lltid/pow(10,11)))), " + DESTARRAY + "), " + DESTARRAY + ");"
	cmd = cmd + afl + " && "
	#Remove temporal arrays
	for an in tmparraylist:
		afl = "remove(" + an + ");"
		cmd = cmd + afl + " && "
	cmd = cmdafl + cmd + "\" ; "
	return cmd


#********************************************************
#WORKER
#********************************************************
def main(argv):
	t0 = datetime.datetime.now()
	parser = argparse.ArgumentParser(description = "Loads a SCIDB's binary file to SCIDB")
	parser.add_argument("binaryFilepath", help = "Path to a binary file (*.sdbbin)")
	parser.add_argument("destArray", help = "3D Array to upload the data to")
	parser.add_argument("-p", "--product", help = "MODIS product. e.g MOD09Q1", default = "default")
	parser.add_argument("-c", "--chunkSize1D", help = "Chunksize for the temporal 1D-array holding the loaded data", type = int, default = 0)
	parser.add_argument("-l", "--loadInstance", help = "SciDB's instance used for uploading the data. Default = coordinator instance", type = int, default = -2)
	parser.add_argument("--log", help = "Log level. Default = WARNING", default = 'WARNING')
	#Get paramters
	args = parser.parse_args()
	binaryFilepath = args.binaryFilepath	
	chunkSize1D = args.chunkSize1D
	destArray = args.destArray
	chunkSize1D = args.chunkSize1D
	loadInstance = args.loadInstance
	prod = args.product
	log = args.log
	####################################################
	# CONFIG
	####################################################
	modisprod = ['MOD09Q1', 'MOD13Q1', 'TRMM_3B43']
	flatArraySchema = {
		'MOD09Q1':	'lltid:int64, red:int16, nir:int16, quality:uint16',
		'MOD13Q1':	'lltid:int64, ndvi:int16, evi:int16, quality:uint16, red:int16, nir:int16, blue:int16, mir:int16, viewza:int16, sunza:int16, relaza:int16, cdoy:int16, reli:int8',
		'TRMM_3B43':'lltid:int64, precipitation:float, relativeError:float, gaugeRelativeWeighting:int8'
	}
	flatArrayChunksize = {
		'MOD09Q1':	1048576, # ~6MB
		'MOD13Q1':	262144, # ~6MB
		'TRMM_3B43':262144 # ~2.25MB
	}
	if prod == 'default':
		for mp in modisprod:
			if mp in binaryFilepath:
				prod = mp
	if prod == 'default':
                logging.exception("Unknown product: The product could not be figured out.")
                raise Exception("Unknown product")
	if prod in modisprod == False:
		logging.exception("Unknown product: Product not found.")
		raise Exception("Product not found")
	flatDimension = '[k=0:*, ' + str(chunkSize1D) + ', 0]'
	if chunkSize1D < 1:
		flatDimension = '[k=0:*, ' + str(flatArrayChunksize[prod]) + ',0]'
	#Log
	numeric_loglevel = getattr(logging, log.upper(), None)
	if not isinstance(numeric_loglevel, int):
		raise ValueError('Invalid log level: %s' % log)
	logging.basicConfig(filename = 'log_load2scidb.log', level = numeric_loglevel, format = '%(asctime)s %(levelname)s: %(message)s')
	logging.info("load2scidb: " + str(args))
	#
	iqpath = "/opt/scidb/" + os.environ['SCIDB_VER'] + "/bin/" # Path to iquery
	cmdaql = iqpath + "iquery -nq \"" # Prefix on how to call iquery with AQL expression
	cmdafl = iqpath + "iquery -naq \"" # Prefix on how to call iquery with AFL expression
	####################################################
	# SCRIPT
	####################################################
	bpath, bfilename = os.path.split(binaryFilepath)	
	TMP_VALUE1D = getArrayname(bfilename)
	flatArrayAQL = "CREATE ARRAY " + TMP_VALUE1D + " <" + flatArraySchema[prod] + ">" + flatDimension + ";"
	load2scidb(binaryFilepath, destArray, flatArrayAQL, cmdaql, cmdafl, loadInstance)
	t1 = datetime.datetime.now()
	tt = t1 - t0
	logging.info("Done in " + str(tt))


if __name__ == "__main__":
   main(sys.argv[1:])
