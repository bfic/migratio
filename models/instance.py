from sqlalchemy import Column, Integer, DateTime, String, Text, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.dialects import postgresql
from sqlalchemy import and_
from sqlalchemy import types
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

import netaddr
import time

BASE = declarative_base()

def MediumText():
    return Text().with_variant(MEDIUMTEXT(), 'mysql')


def get_shortened_ipv6(address):
    addr = netaddr.IPAddress(address, version=6)
    return str(addr.ipv6())


def is_valid_ipv6(address):
    """Verify that address represents a valid IPv6 address.

    :param address: Value to verify
    :type address: string
    :returns: bool
    """
    try:
        return netaddr.valid_ipv6(address)
    except Exception:
        return False


class IPAddress(types.TypeDecorator):
    """An SQLAlchemy type representing an IP-address."""

    impl = types.String

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(postgresql.INET())
        else:
            return dialect.type_descriptor(types.String(39))

    def process_bind_param(self, value, dialect):
        """Process/Formats the value before insert it into the db."""
        if dialect.name == 'postgresql':
            return value
        # NOTE(maurosr): The purpose here is to convert ipv6 to the shortened
        # form, not validate it.
        elif is_valid_ipv6(value):
            return get_shortened_ipv6(value)
        return value


class Instance(BASE):
    """Represents a guest VM."""
    __tablename__ = 'instances'
    injected_files = []

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(String(255))
    project_id = Column(String(255))
    deleted = Column(Integer)

    image_ref = Column(String(255))
    kernel_id = Column(String(255))
    ramdisk_id = Column(String(255))
    hostname = Column(String(255))

    launch_index = Column(Integer)
    key_name = Column(String(255))
    key_data = Column(MediumText())

    power_state = Column(Integer)
    vm_state = Column(String(255))
    task_state = Column(String(255))

    memory_mb = Column(Integer)
    vcpus = Column(Integer)
    root_gb = Column(Integer)
    ephemeral_gb = Column(Integer)
    ephemeral_key_uuid = Column(String(36))

    # This is not related to hostname, above.  It refers
    #  to the nova node.
    host = Column(String(255))  # , ForeignKey('hosts.id'))
    # To identify the "ComputeNode" which the instance resides in.
    # This equals to ComputeNode.hypervisor_hostname.
    node = Column(String(255))

    # *not* flavorid, this is the internal primary_key
    instance_type_id = Column(Integer)

    user_data = Column(MediumText())

    reservation_id = Column(String(255))

    scheduled_at = Column(DateTime)
    launched_at = Column(DateTime)
    terminated_at = Column(DateTime)

    availability_zone = Column(String(255))

    # User editable field for display in user-facing UIs
    display_name = Column(String(255))
    display_description = Column(String(255))

    # To remember on which host an instance booted.
    # An instance may have moved to another host by live migration.
    launched_on = Column(MediumText())

    # NOTE(jdillaman): locked deprecated in favor of locked_by,
    # to be removed in Icehouse
    locked = Column(Boolean)
    locked_by = Column(Enum('owner', 'admin'))

    os_type = Column(String(255))
    architecture = Column(String(255))
    vm_mode = Column(String(255))
    uuid = Column(String(36), nullable=False)

    root_device_name = Column(String(255))
    default_ephemeral_device = Column(String(255))
    default_swap_device = Column(String(255))
    config_drive = Column(String(255))

    # User editable field meant to represent what ip should be used
    # to connect to the instance
    access_ip_v4 = Column(IPAddress())
    access_ip_v6 = Column(IPAddress())

    auto_disk_config = Column(Boolean())
    progress = Column(Integer)

    # EC2 instance_initiated_shutdown_terminate
    # True: -> 'terminate'
    # False: -> 'stop'
    # Note(maoy): currently Nova will always stop instead of terminate
    # no matter what the flag says. So we set the default to False.
    shutdown_terminate = Column(Boolean(), default=False)

    # EC2 disable_api_termination
    disable_terminate = Column(Boolean(), default=False)

    # OpenStack compute cell name.  This will only be set at the top of
    # the cells tree and it'll be a full cell name such as 'api!hop1!hop2'
    cell_name = Column(String(255))
    internal_id = Column(Integer)

    # Records whether an instance has been deleted from disk
    cleaned = Column(Integer, default=0)

def connect_to_sqlalchemy(connection_string):
    """
    Creates a connection to Openstack's database and returns
    a session class.
    """

    engine = create_engine(connection_string, echo=False, poolclass=NullPool)
    session_maker = sessionmaker(bind=engine)
    session = None

    """ Check if sessions are not empty """
    i = 0
    for i in range(1, 5):
        print("create Openstack's db session")
        session = session_maker()
        if session:
            print("Connection to OS's database was established successfully")
            break
        print("Problem with OS's database connection, retrying")
        time.sleep(1)
        engine = create_engine(connection_string, echo=False, poolclass=NullPool)
        session_maker.configure(bind=engine)

    if i == 5 and not session:
        print("Unable to connect to OS's database")
        raise Exception()

    return sessionmaker(bind=engine)
