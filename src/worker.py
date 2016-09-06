#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import pika
import time
from pymongo import MongoClient
import gridfs
from bson.objectid import ObjectId
import pandas as pd
from brandExitConversion import brandExitMung
from preoptimizerR4 import preoptimize
from optimizerR4 import optimize
# from CurveFitting import curveFittingBS
# from DataMerging import dataMerging
from pulp import *
import config
# from TierKey import tierKeyCreate
# from TierOptim import tierDef

JOB_STATUS = {
    'QUEUED':'QUEUED',
    'RUNNING':'RUNNING',
    'DONE':'DONE'
}

def main():
    def make_serializable(db_object):
        if '_id' in db_object:
            db_object['_id'] = str(db_object['_id'])
        if 'uploadDate' in db_object:
            db_object['uploadDate'] = db_object['uploadDate'].isoformat()
        return db_object

    db = MongoClient(config.MONGO_CON)['app']
    fs = gridfs.GridFS(db)

    # my_test_file = fs.get(ObjectId("577eabb51d41c808371a6092")).read()
    
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=config.RABBIT_URL))
    channel = connection.channel()

    channel.queue_declare(queue='task_queue', durable=True)
    channel.queue_declare(queue='notify_queue', durable=False)
    print(' [*] Waiting for messages. To exit press CTRL+C')

    def callback(ch, method, properties, body):
        # print(" [x] Received %r" % body)

        msg = json.loads(body.decode('utf-8'))
        # Find job to check status of job
        job = db.jobs.find_one({'_id': ObjectId(msg['_id'])})
        try:
            job_id = job['_id']
        except TypeError as e:
            print('Job Not Found')
            return False

        # current_user = job['userId']
        # job_status = job['status']

        db.jobs.update_one(
            {'_id': job['_id']},
            {
                "$set": {
                    "status": "running"
                }
            }
        )

        def fetch_artifact(artifact_id):    
            file = fs.get(ObjectId(artifact_id))
            file = pd.read_csv(file,header=0)
            return file

        def create_output_artifact_from_dataframe(dataframe, *args, **kwargs):
            return fs.put(dataframe.to_csv().encode(), **kwargs)
        '''
        # masterData=dataMerging(msg["jobType"])
        # try:
            # msg["optimizedMetrics"]['sales']
            # cfbs=curveFittingBS(masterData,spaceBounds,increment,100,0,0,msg['storeCategoryBounds'],msg['optimizationType'])
        # except:
            # cfbs=curveFittingBS(masterData,spaceBounds,increment,optimizedMetrics['sales'],optimizedMetrics['profits'],optimizedMetrics['units'],msg['storeCategoryBounds'],msg['optimizationType'])
        # create_output_artifact_from_dataframe(cfbs[0])
        # create_output_artifact_from_dataframe(cfbs[1])        
        '''
        fixtureArtifact=fetch_artifact(msg["artifacts"]["spaceArtifactId"])
        transactionArtifact=fetch_artifact(msg["artifacts"]["salesArtifactId"])
        transactionArtifact=transactionArtifact.drop(transactionArtifact.index[[0]]).set_index("Store")
        fixtureArtifact=fixtureArtifact.drop(fixtureArtifact.index[[0]]).set_index("Store")
        Stores=fixtureArtifact.index.values.astype(int)
        Categories=fixtureArtifact.columns[2:].values
        print("There are "+str(len(Stores)) + " and " + str(len(Categories)) + " Categories")
        print(msg['optimizationType'])
        try:
            futureSpace=fetch_artifact(msg["artifacts"]["futureSpaceId"]).set_index("Store")
            print("Future Space was Uploaded")
        except:
            futureSpace=None
            print("Future Space was not Uploaded")
        try:
            brandExitArtifact=fetch_artifact(msg["artifacts"]["brandExitArtifactId"])
            print("Brand Exit was Uploaded")
            brandExitArtifact=brandExitMung(brandExitArtifact,Stores,Categories)
            print("Brand Exit Munged")
        except:
            print("Brand Exit was not Uploaded")
            brandExitArtifact=None
        msg["optimizationType"]='traditional'
        if (str(msg["optimizationType"]) == 'traditional'):
            preOpt = preoptimize(Stores=Stores,Categories=Categories,spaceData=fixtureArtifact,data=transactionArtifact,mAdjustment=float(msg["metricAdjustment"]),salesPenThreshold=float(msg["salesPenetrationThreshold"]),optimizedMetrics=msg["optimizedMetrics"],increment=msg["increment"],brandExitArtifact=brandExitArtifact,newSpace=futureSpace)
            optimizationStatus=optimize(job_id,preOpt,msg["tierCounts"],msg["spaceBounds"],msg["increment"],fixtureArtifact,brandExitArtifact)
        if (msg["optimizationType"] == 'enhanced'):
            print("Ken hasn't finished development for that yet")
            # set status to done
        db.jobs.update_one(
            {'_id': job['_id']},
            {
                "$set": {
                    "status": "done"
                }
            }
        )

        res = dict(
            job_id=msg['_id'],
            user_id=msg['userId'],
            outcome='Success'
        )

        # send notification
        ch.basic_ack(delivery_tag=method.delivery_tag)
        channel.basic_publish(exchange='',
                              routing_key='notify_queue',
                              # body='Job: 123 requested by userId: 456 is done!',
                              body=json.dumps(res),
                              properties=pika.BasicProperties(
                                  # delivery_mode=2,  # make message persistent
                              ))

        print(" [x] Done")

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(callback,
                          queue='task_queue')

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        connection.close()


if __name__ == '__main__':
    
    main()
