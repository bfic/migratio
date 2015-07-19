from modules import Instance

from subprocess import call
import os

sessionmaker = connect_to_sqlalchemy("mysql+pymysql://root:intel@lm-1/nova?charset=utf8")

vms_to_migrate = []
vms_migrated = []
sim_migrations = 1

"""
OS_REGION_NAME=RegionOne
OS_IDENTITY_API_VERSION=2.0
OS_PASSWORD=password
OS_AUTH_URL=http://localhost:5000/v2.0
OS_USERNAME=admin
OS_TENANT_NAME=demo
OS_VOLUME_API_VERSION=2
OS_NO_CACHE=1
"""

os.environ['OS_NO_CACHE']="1"
os.environ['OS_REGION_NAME']="RegionOne"
os.environ['OS_IDENTITY_API_VERSION']="2.0"
os.environ['OS_PASSWORD']="password"
os.environ['OS_AUTH_URL']="http://localhost:5000/v2.0"
os.environ['OS_USERNAME']="admin"
os.environ['OS_TENANT_NAME']="demo"
os.environ['OS_VOLUME_API_VERSION']="2"

while True:
    session = sessionmaker()
    if not vms_to_migrate:
        vms_to_migrate = session.query(Instance.uuid).filter(and_(
            Instance.deleted==False, 
            Instance.vm_state=='active', 
            Instance.task_state==None)
        ).all()
    if not vms_to_migrate:
        print "No VMs found, sleeping 5 secs..."
        time.sleep(5)
        continue
    migrating_vms_count = session.query(Instance.uuid).filter_by(task_state='migrating').count()
    if migrating_vms_count < sim_migrations:
        vm_uuid = vms_to_migrate[0][0]
        print "Migrating: " + vm_uuid
        del vms_to_migrate[0] 
        os.system("nova live-migration " + vm_uuid)
    else:
        print "Waiting for migration to finish..."
    #for result in result_list:
    #    print result.display_name
    session.close()
    time.sleep(2)

