import sys
import re
import logging
import random
import struct
import socket
import importlib
import os
import xml.etree.ElementTree as etree
xml_gen = importlib.import_module('dice.utils.xml_gen')
utils_random = importlib.import_module('dice.utils.rnd')


UNIT_MAP = {
    "b": 1,
    "byte": 1,
    "k": 1000**1,
    "m": 1000**2,
    "g": 1000**3,
    "t": 1000**4,
    "p": 1000**5,
    "e": 1000**6,
    "kb": 1000**1,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
    "pb": 1000**5,
    "eb": 1000**6,
    "kib": 1024**1,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
    "pib": 1024**5,
    "eib": 1024**6,
}

OVERIDE_MAP = {
    "element": [
        ("/domain/metadata", None, "ignore_metadata"),
        ("/domain/bootloader(|_args)", None, "ignore_bootloader"),
        ("/domain/cpu/(vendor|feature)", None, "only_with_model"),
        ("/domain/devices/(interface|hostdev|disk|redirdev)/boot", None,
         "ignore_if_os_boot_exists"),
        ("/domain/numatune/memnode", None, "only_with_strict_placement"),
        ("/domain/cputune/vcpusched", None, "ignore_vcpusched_if_no_vcpu"),
        ("/domain/cpu/numa/cell", None, "ignore_cell_if_no_vcpu"),
        ("/domain/cputune/iothreadsched", None, "ignore_if_no_iothread"),
        ("/domain/keywrap/cipher", None, "ignore_cipher_if_both_exists"),
        ("/domain/.*seclabel", None, "seclabel"),
    ],
    "define": [
    ],
    "optional": [
        ("/domain", None, "domain_optional"),
    ],
    "attribute": [
        ("/domain/type", None, "domain_type"),
        ("/domain/vcpu/current", None, "current_vcpu"),
        ("/domain/cputune/vcpupin/vcpu", None, "vcpupin_cpu"),
        ("/domain/memoryBacking/hugepages/page/nodeset", None,
         "hugepage_nodeset"),
        ("/domain/memoryBacking/hugepages/page/size", None, "hugepage_size"),
        ("/domain/devices/video/model/vgamem", None, "vgamem"),
        ("/domain/devices/disk/target/removable", None, "disk_removable"),
        ("/domain/devices/disk/target/tray", None, "disk_tray"),
        ("/domain/devices/disk/target/bus", None, "disk_bus"),
        ("/domain/cpu/numa/cell/id", None, "numa_id"),
        ("/domain/cpu/numa/cell/memory", None, "cell_memory"),
        ("/domain/cpu/numa/cell/unit", None, "cell_memory_unit"),
        ("/domain/devices/interface/bandwidth/inbound/floor", None,
         "iface_inbound_floor"),
        ("/domain/devices/interface/bandwidth/outbound/floor", None,
         "iface_outbound_floor"),
        ("/domain/maxMemory/unit", None, "max_mem_unit"),
        ("/domain/memory/unit", None, "actual_mem_unit"),
        ("/domain/currentMemory/unit", None, "cur_mem_unit"),
        ("/domain/numatune/memnode/cellid", None, "numatune_cellid"),
        ("/domain/devices/disk/driver/event_idx", None, "disk_virtio"),
        ("/domain/devices/disk/driver/ioeventfd", None, "disk_virtio"),
        ("/domain/cputune/iothreadsched/iothreads", None,
         "iothreadsched_iothreads"),
        ("/domain/cputune/iothreadpin/iothread", None, "iothreadpin_iothread"),
        ("/domain/iothreadids/iothread/id", None, "iothread_id"),
        ("/domain/features/hyperv/spinlocks/retries", None,
         "hyperv_spinlock_retries"),
        ("/domain/idmap/uid/start", None, "idmap_root"),
        ("/domain/idmap/gid/start", None, "idmap_root"),
        ("/domain/devices/console/source/mode", None, "source_mode"),
        ("/domain/devices/channel/source/mode", None, "source_mode"),
        ("/domain/devices/serial/source/mode", None, "source_mode"),
        ("/domain/devices/parallel/source/mode", None, "source_mode"),
        ("/domain/devices/smartcard/source/mode", None, "source_mode"),
        ("/domain/devices/redirdev/source/mode", None, "source_mode"),
        ("/domain/devices/interface/vlan/tag/nativeMode", None, "vlan_native"),
        ("/domain/devices/hostdev/source/startupPolicy", None,
         "hostdev_startpol"),
        ("/domain/devices/hostdev/source/address/device", None,
         "hostdev_device"),
        ("/domain/devices/interface/source/address/device", None,
         "hostdev_device"),
        ("/domain/devices/graphics/listen/address", None, "listen_address"),
        ("/domain/devices/interface/model/type", None, "iface_model"),
        ("/domain/devices/interface/ip/family", None, "ip_family"),
        ("/domain/devices/interface/route/netmask", None, "route_netmask"),
        ("/domain/.*seclabel/model", None, "seclabel_model"),
        ("/domain/devices/nvram/address", None, "dimm_base"),
        ("/controller/address/bus", None, "controller_bus"),
    ],
    "zeroOrMore": [
        ("/domain/cputune", '/define\[@name="cpuquota"\]/data/zeroOrMore',
         "vcpupin"),
        ("/domain/idmap", None, "idmap"),
        ("/domain/devices/parallel", None, "dev_source"),
        ("/domain/devices/serial", None, "dev_source"),
        ("/domain/devices/console", None, "dev_source"),
        ("/domain/devices/redirdev", None, "dev_source"),
        ("/domain/devices/channel", None, "dev_source"),
        ("/domain/devices/smartcard", None, "dev_source"),
        ("/domain/devices/rng/backend", None, "dev_source"),
    ],
    "oneOrMore": [
        ("/domain/cpu/numa", None, "numa_cnt"),
    ],
    "data": [
        (None, '/define\[@name="cpuset"\]/data', "cpuset"),
        (None, '/define\[@name="countCPU"\]/data', "max_vcpu"),
        (None, '/define\[@name="(pciDomain|pciBus|pciSlot|pciFunc|usbAddr|'
         'usbClass|usbId)"\]/data', "hexdec"),
        (None, '/define\[@name="usbPort"\]/data', "usbport"),
        (None, '/define\[@name="timeDelta"\]/data', "time_delta"),
        ('/domain/iothreads', None, "max_iothread"),
        ("/domain/maxMemory", None, "max_mem"),
        ("/domain/memory", None, "act_mem"),
        ("/domain/currentMemory", None, "cur_mem"),
        ("/domain/iothreads", None, "iothreads"),
        ("/domain/devices/disk/target", None, "disk_target"),
        ("/domain/sysinfo/bios/entry", None, "sysinfo_entry"),
        ("/domain/sysinfo/system/entry", None, "sysinfo_entry"),
        ("/domain/devices/emulator", None, "qemu_path"),
    ],
    "choice": [
        ("/domain/devices/redirdev/address", None, "redirdev_address"),
        ("/domain/devices/input/address", None, "input_address"),
        ("/domain/seclabel", None, "seclabel"),
        ("/domain/devices/interface/address", None, "pci_address"),
        ("/domain/devices/controller/address", None, "pci_address"),
        ("/domain/devices/controller", None, "controller_model"),
        ("/domain/devices/serial/address", None, "serial_address"),
        ("/domain/devices/disk/address", None, "disk_address"),
        ("/domain/devices/hostdev/address", None, "hostdev_address"),
        ("/domain/devices/console/target", None, "char_target"),
        ("/domain/devices/serial/target", None, "char_target"),
        ("/domain/devices/channel", None, "channel_target"),
        ("/domain/devices/hostdev", None, "hostdev_mode"),
        ("/domain/devices/graphics/listen", None, "listen_type"),
        ("/domain/devices/console", None, "char_type"),
        ("/domain/devices/serial", None, "char_type"),
        ("/domain/devices/parallel", None, "char_type"),
        ("/domain/devices/input", None, "input_bus"),
        ("/domain/devices/disk/source", None, "disk_source"),
        ("/domain/devices/interface/route", '/define\[@name="ipAddr"\]/choice',
         "address_family"),
        ("/domain/keywrap/cipher", None, "cipher_name"),
    ],
    "ref": [
    ],
    "empty": [
    ],
    "group": [
    ],
    "value": [
    ],
    "interleave": [
    ],
    "text": [
    ],
    "start": [
    ],
    "anyName": [
    ],
    "anyURI": [
    ],
}


def definable(function):
    def _inner(*args, **kargs):
        instance = args[0]
        sanity = instance.params['sanity']
        if sanity in ['definable', 'startable']:
            result = function(*args, **kargs)
            return result
        else:
            instance.cont = True
            return
    return _inner


def startable(function):
    def _inner(*args, **kargs):
        instance = args[0]
        sanity = instance.params['sanity']
        if sanity in ['startable']:
            result = function(*args, **kargs)
            return result
        else:
            instance.cont = True
            return
    return _inner


def load_rng(file_name, is_root=True):
    xml_str = open(file_name).read()
    xml_str = re.sub(' xmlns="[^"]+"', '', xml_str, count=1)
    nodetree = etree.fromstring(xml_str)
    xml_path = os.path.dirname(file_name)
    for node in nodetree.findall('./include'):
        rng_name = os.path.join(xml_path, node.attrib['href'])
        nodetree.remove(node)
        for element in load_rng(rng_name, is_root=False):
            nodetree.insert(0, element)
    return nodetree if is_root else nodetree.getchildren()


def node_overide(rng, nodetree):
    fname = os.path.split(rng)[1] + '_overides.xml'
    for element in load_rng(fname, is_root=False):
        name = element.get('name')
        node = nodetree.find('./define[@name="%s"]' % name)
        if node is not None:
            nodetree.remove(node)

        nodetree.insert(0, element)


def process_overide(tag, xml_path, node_path, node, params):
    logging.debug('%s %s %s', tag, xml_path, node_path)
    if tag not in OVERIDE_MAP:
        logging.error('Unknown tag %s' % tag)
        return

    cont = True
    result = None
    for xml_patt, node_patt, func_name in OVERIDE_MAP[tag]:
        if xml_patt is None or re.match('^' + xml_patt + '$', xml_path):
            if node_patt is None or re.match('^' + node_patt + '$', node_path):
                cls_name = 'Process' + tag.capitalize()
                process_instance = globals()[cls_name]()
                cont, result = process_instance.process(
                    func_name, node, xml_path, node_path, params)

    return cont, result


class ProcessBase(object):

    def process(self, func_name, node, xml_path, node_path, params):
        self.xml_path = xml_path
        self.node_path = node_path
        self.params = params
        self.xml_stack = params['xml_stack']
        self.xml = self.xml_stack[0]
        self.cur_xml = self.xml_stack[-1]
        self.parent = None
        if len(self.xml_stack) > 1:
            self.parent = self.xml_stack[-2]
        self.node = node
        self.nodetree = params['nodetree']
        self.name = node.get('name')
        self.cont = False

        result = getattr(self, func_name)()

        return self.cont, result

    def go_on(self):
        self.cont = True

    def get_max_vcpu(self):
        if 'max_vcpu' in self.params:
            cnt = self.params['max_vcpu']
        else:
            cnt = self.params['max_vcpu'] = utils_random.int_exp(1)
        return cnt

    def get_max_mem(self):
        if 'maxmem' in self.params:
            maxmem = self.params['maxmem']
            unit = self.params['maxmem_unit']
        else:
            maxmem = utils_random.integer(1, 10000000)
            unit = 'eib'
            while maxmem <= UNIT_MAP[unit]:
                unit = random.choice(list(UNIT_MAP.keys()))
            maxmem /= UNIT_MAP[unit]
            maxmem *= UNIT_MAP[unit]
            self.params['maxmem'] = maxmem
            self.params['maxmem_unit'] = unit
        return maxmem, unit

    def get_max_iothread(self):
        if 'max_iothread' in self.params:
            cnt = self.params['max_iothread']
        else:
            cnt = self.params['max_iothread'] = utils_random.int_exp(1)
        return cnt

    def get_cell_vcpus(self):
        if 'cell_vcpus' in self.params:
            cnt = self.params['cell_vcpus']
        else:
            cnt = self.params['cell_vcpus'] = set()
        return cnt

    def get_vcpusched(self):
        if 'vcpusched' in self.params:
            cnt = self.params['vcpusched']
        else:
            cnt = self.params['vcpusched'] = set()
        return cnt

    def get_iothreadsched(self):
        if 'iothreadsched' in self.params:
            cnt = self.params['iothreadsched']
        else:
            cnt = self.params['iothreadsched'] = set()
        return cnt


class ProcessElement(ProcessBase):

    def ignore_metadata(self):
        pass

    @definable
    def ignore_bootloader(self):
        pass

    @definable
    def only_with_model(self):
        if self.xml.find('./cpu/model') is not None:
            if self.xml.find('./cpu/model').text:
                return self.go_on()

    @definable
    def ignore_if_os_boot_exists(self):
        if self.xml.find('./os/boot') is None:
            return self.go_on()

    @definable
    def only_with_strict_placement(self):
        placement = self.xml.find('./numatune/memory').get('placement')
        if placement == 'strict':
            return self.go_on()

    @definable
    def ignore_vcpusched_if_no_vcpu(self):
        used_vcpus = len(self.get_vcpusched())
        if used_vcpus < self.params['max_vcpu']:
            return self.go_on()

    @definable
    def ignore_cell_if_no_vcpu(self):
        used_vcpus = len(self.get_cell_vcpus())
        if used_vcpus < self.params['max_vcpu']:
            return self.go_on()

    @definable
    def ignore_if_no_iothread(self):
        used_iothreads = len(self.get_iothreadsched())
        if used_iothreads < self.params['max_iothread']:
            return self.go_on()

    @definable
    def ignore_cipher_if_both_exists(self):
        has_aes = self.cur_xml.find('./cipher[@name="aes"]') is not None
        has_dea = self.cur_xml.find('./cipher[@name="dea"]') is not None
        if not (has_aes and has_dea):
            return self.go_on()

    @startable
    def seclabel(self):
        # TODO: Check whether all kind of seclabels are used.
        models = ['none', 'dac']
        for seclabel in self.cur_xml.findall('./seclabel'):
            model = seclabel.get('model')
            if model is not None:
                models.remove(model)
        if models:
            return self.go_on()


class ProcessAttribute(ProcessBase):

    def process(self, func_name, node, xml_path, node_path, params):
        _, result = super(ProcessAttribute, self).process(
            func_name, node, xml_path, node_path, params)

        if type(result) is str:
            self.cur_xml.set(self.name, result)
        elif result is not None:
            logging.error("Attribute should be a string, but %s found",
                          type(result))
        return self.cont, None

    @definable
    def domain_type(self):
        # TODO: detect available domain types.
        types = random.choice(["qemu", "kvm"])
        return types

    @definable
    def numa_id(self):
        if 'numa_maxid' not in self.params:
            self.params['numa_maxid'] = 0
        else:
            self.params['numa_maxid'] += 1
        return str(self.params['numa_maxid'])

    @definable
    def cell_memory(self):
        maxmem, _ = self.get_max_mem()
        if 'left_numa_mem' not in self.params:
            self.params['left_numa_mem'] = maxmem
        left_mem = self.params['left_numa_mem']
        mem = utils_random.integer(1, left_mem)
        unit = 'eib'
        while mem <= UNIT_MAP[unit]:
            unit = random.choice(list(UNIT_MAP.keys()))
        mem /= UNIT_MAP[unit]
        mem *= UNIT_MAP[unit]
        self.params['left_numa_mem'] -= mem
        self.params['cell_mem_unit'] = unit
        #print 'cell', self.params['left_numa_mem'], self.params['cell_mem_unit']
        return str(mem / UNIT_MAP[self.params['cell_mem_unit']])

    @definable
    def cell_memory_unit(self):
        return self.params['cell_mem_unit']

    @definable
    def current_vcpu(self):
        max_vcpu = self.get_max_vcpu()
        cnt = utils_random.integer(1, max_vcpu)
        return str(cnt)

    @definable
    def vcpupin_cpu(self):
        max_vcpu = self.get_max_vcpu()
        if 'unpined_cpus' in self.params:
            unpined_cpus = self.params['unpined_cpus']
        else:
            unpined_cpus = self.params['unpined_cpus'] = set(range(max_vcpu))
        cpuid = random.choice(list(unpined_cpus))
        self.params['unpined_cpus'].remove(cpuid)
        return str(cpuid)

    @definable
    def hugepage_nodeset(self):
        if 'hugecpus' in self.params:
            hugecpus = self.params['hugecpus']
        else:
            hugecpus = self.params['hugecpus'] = []

        cpu = int(random.expovariate(1))
        while cpu in hugecpus:
            cpu = int(random.expovariate(1))

        hugecpus.append(cpu)
        return str(cpu)

    @definable
    def hugepage_size(self):
        size = int(random.expovariate(0.1)) + 1
        return str(size)

    @definable
    def vgamem(self):
        size = 2**(int(random.expovariate(1)) + 10)
        return str(size)

    @definable
    def disk_removable(self):
        if self.cur_xml.get('bus') == 'usb':
            return self.go_on()

    @definable
    def disk_tray(self):
        if self.cur_xml.get('bus') in ['floppy', 'cdrom']:
            return self.go_on()

    @definable
    def disk_bus(self):
        if self.parent.find('./driver[@iothread]') is not None:
            return 'virtio'

        if self.parent.get('device') == 'floppy':
            return 'fdc'

    @definable
    def iface_inbound_floor(self):
        # TODO: This should be checked
        if self.xml_stack[-3].get('type') != 'network':
            pass

    @definable
    def iface_outbound_floor(self):
        # TODO: This should be checked
        pass

    @definable
    def max_mem_unit(self):
        _, unit = self.get_max_mem()
        return str(unit)

    @definable
    def actual_mem_unit(self):
        maxmem, _ = self.get_max_mem()
        actmem = utils_random.integer(1, maxmem)
        unit = 'eib'
        while actmem <= UNIT_MAP[unit]:
            unit = random.choice(list(UNIT_MAP.keys()))
        actmem /= UNIT_MAP[unit]
        actmem *= UNIT_MAP[unit]
        self.params['actmem'] = actmem
        self.params['actmem_unit'] = unit
        return str(unit)

    @definable
    def cur_mem_unit(self):
        actmem = self.params['actmem']
        curmem = utils_random.integer(1, actmem)
        unit = 'eib'
        while curmem <= UNIT_MAP[unit]:
            #print unit, list(UNIT_MAP.keys())
            unit = random.choice(list(UNIT_MAP.keys()))
        curmem /= UNIT_MAP[unit]
        curmem *= UNIT_MAP[unit]
        self.params['curmem'] = curmem
        self.params['curmem_unit'] = unit
        #print 'maxmem', self.params['maxmem'], self.params['maxmem_unit']
        #print 'actmem', self.params['actmem'], self.params['actmem_unit']
        #print 'curmem', self.params['curmem'], self.params['curmem_unit']
        return str(unit)

    @definable
    def numatune_cellid(self):
        n = utils_random.integer(0, self.params['numa_maxid'])
        return str(n)

    @definable
    def disk_virtio(self):
        if self.parent.get('device') != 'floppy':
            return self.go_on()

    @definable
    def iothreadsched_iothreads(self):
        return self.go_on()

    @definable
    def iothreadpin_iothread(self):
        iothreads = self.params['iothreads']
        iothread = utils_random.integer(0, iothreads)
        return str(iothread)

    @definable
    def iothread_id(self):
        iothreads = self.params['iothreads']
        if 'iothreadids' not in self.params:
            self.params['iothreadids'] = set()
        ids = self.params['iothreadids']

        tid = utils_random.integer(0, iothreads)
        while tid in ids and len(ids) < iothreads:
            tid = utils_random.integer(0, iothreads)
        self.params['iothreadids'].add(tid)
        return str(tid)

    @definable
    def hyperv_spinlock_retries(self):
        retries = utils_random.integer(4095, 100000000)
        return str(retries)

    @definable
    def idmap_root(self):
        return '0'

    @definable
    def source_mode(self):
        if self.parent.get('type') not in ['udp', 'tcp']:
            return self.go_on()

        mode = random.choice(['connect', 'bind', None])
        if mode is not None:
            return mode

    @definable
    def vlan_native(self):
        if self.parent.find('./tag[@nativeMode]') is None:
            return self.go_on()

    @definable
    def hostdev_startpol(self):
        if self.parent.get('type') == 'usb':
            return self.go_on()

    @definable
    def hostdev_device(self):
        # TODO: There should be a bug
        dev = utils_random.integer(0, 99999)
        return str(dev)

    @definable
    def listen_address(self):
        listen = self.parent.get('listen')
        if listen is None:
            return self.go_on()
        return listen

    @definable
    def iface_model(self):
        iface_type = self.parent.get('type')
        if iface_type != 'vhostuser':
            return self.go_on()

        return 'virtio'

    @definable
    def ip_family(self):
        family = 'ipv4'
        if ':' in self.cur_xml.get('address'):
            family = 'ipv6'
        return family

    @startable
    def seclabel_model(self):
        # TODO: Add check for support of security
        models = ['none', 'dac']
        for seclabel in self.parent.findall('./seclabel'):
            model = seclabel.get('model')
            if model is not None:
                models.remove(model)
        if not models:
            logging.error('models should not be empty')

        model = random.choice(models)
        return model

    @definable
    def dimm_base(self):
        sys.stdout.write(self.cur_xml)
        pass

    @definable
    def route_netmask(self):
        def _ip2int(addr):
            return struct.unpack("!I", socket.inet_aton(addr))[0]

        def _int2ip(addr):
            return socket.inet_ntoa(struct.pack("!I", addr))

        address = self.cur_xml.get('address')
        if ':' in address:
            return self.go_on()

        int_addr = _ip2int(address)
        prefix = utils_random.integer(0, 32)
        int_nm = (2**prefix - 1) * 2**(32 - prefix)

        netmask = _int2ip(int_nm)
        address = _int2ip(int_nm & int_addr)
        self.cur_xml.set('address', address)
        return netmask

    @definable
    def controller_bus(self):
        index = int(self.parent.get('index'))
        cnt = utils_random.int_exp(max_inc=index)
        return str(cnt)


class ProcessData(ProcessBase):

    @definable
    def max_vcpu(self):
        return str(self.get_max_vcpu())

    @definable
    def max_iothread(self):
        return str(self.get_max_iothread())

    @definable
    def cpuset(self):
        used_vcpu = set()
        min_inc = 0
        max_inc = self.params['max_vcpu'] - 1

        if self.xml_path == '/domain/cputune/vcpusched':
            used_vcpu = self.get_vcpusched()
        if self.xml_path == '/domain/cpu/numa/cell':
            used_vcpu = self.get_cell_vcpus()
        if self.xml_path == '/domain/cputune/iothreadsched':
            used_vcpu = self.get_iothreadsched()
            min_inc = 1
            max_inc = self.params['max_iothread']

        result = utils_random.cpuset(
            min_inc=min_inc,
            max_inc=max_inc,
            used_vcpu=used_vcpu,
        )

        return result

    @definable
    def hexdec(self):
        min_val = 0
        max_val = 9999
        only_dec = False
        if 'pciDomain' in self.node_path:
            pass
        elif 'pciBus' in self.node_path:
            max_val = 99
        elif 'pciSlot' in self.node_path:
            min_val = 1
            max_val = 19
        elif 'pciFunc' in self.node_path:
            max_val = 7
        elif 'usbAddr' in self.node_path:
            max_val = 999
            only_dec = True
        elif 'usbClass' in self.node_path:
            max_val = 99
        elif 'usbId' in self.node_path:
            pass
        n = utils_random.integer(min_val, max_val)
        if only_dec:
            s = str(n)
        else:
            s = random.choice([str(n), hex(n)])
        return s

    @definable
    def usbport(self):
        max_val = 999
        cnt = utils_random.integer(1, 4)
        return '.'.join([str(utils_random.integer(0, max_val))
                         for i in range(cnt)])

    @definable
    def time_delta(self):
        num = utils_random.int_exp(lambd=10)
        if random.random() < 0.5:
            num = -num
        return str(num)

    @definable
    def sysinfo_entry(self):
        name = self.cur_xml.get('name')
        if name not in ['date', 'uuid']:
            return self.go_on()
        if name == 'date':
            data = "01/01/1970"
        elif name == 'uuid':
            data = self.xml.find('./uuid').text
        return data

    @definable
    def max_mem(self):
        return str(self.params['maxmem'] /
                   UNIT_MAP[self.params['maxmem_unit']])

    @definable
    def act_mem(self):
        return str(self.params['actmem'] /
                   UNIT_MAP[self.params['actmem_unit']])

    @definable
    def cur_mem(self):
        return str(self.params['curmem'] /
                   UNIT_MAP[self.params['curmem_unit']])

    @definable
    def iothreads(self):
        self.params['iothreads'] = utils_random.integer(1, 1000)
        return str(self.params['iothreads'])

    @definable
    def qemu_path(self):
        return '/usr/bin/qemu-kvm'

    @definable
    def disk_target(self):
        device = self.parent.get('device')
        if device == 'floppy':
            data = utils_random.regex(r'(ioemu:)?fd[a-zA-Z0-9_]+')
        elif device in ['lun', 'disk']:
            data = utils_random.regex(
                r'(ioemu:)?(hd|sd|vd|xvd|ubd)[a-zA-Z0-9_]+')
        else:
            return self.go_on()
        return data


class ProcessOptional(ProcessBase):

    @definable
    def domain_optional(self):
        # TODO: Move to other place
        if self.node.find("./ref[@name='qemucmdline']") is None:
            return self.go_on()

        controller = self.xml.find("./devices/controller[@type='pci']")
        if controller is None:
            node = self.nodetree.find("./define[@name='pciController']")
            params = {
                'xml_stack': [],
                'node_stack': [],
                'nodetree': self.nodetree,
            }
            pcinode = xml_gen.parse_node(node, params=params)
            self.xml.find("./devices").append(pcinode)


class ProcessZeroormore(ProcessBase):

    def process(self, func_name, node, xml_path, node_path, params):
        _, result = super(ProcessZeroormore, self).process(
            func_name, node, xml_path, node_path, params)

        if type(result) is int:
            child = list(self.node)[0]
            for i in range(result):
                xml_gen.parse_node(child, params=self.params)
        elif result is not None:
            logging.error("ZeroOrMore should return an int, but %s found",
                          type(result))

        return self.cont, None

    @definable
    def vcpupin(self):
        max_vcpu = self.get_max_vcpu()
        return utils_random.integer(0, max_vcpu)

    @definable
    def idmap(self):
        if self.xml.find('./idmap/uid') is None:
            return
        max_vcpu = self.get_max_vcpu()
        return utils_random.integer(1, max_vcpu)

    @definable
    def dev_source(self):
        if self.cur_xml.get('type') not in [
                'dev', 'file', 'unix', 'pipe', 'udp', 'tcp', 'spiceport']:
            return self.go_on()
        return utils_random.int_exp(1)


class ProcessOneormore(ProcessBase):

    def process(self, func_name, node, xml_path, node_path, params):
        _, result = super(ProcessOneormore, self).process(
            func_name, node, xml_path, node_path, params)

        if type(result) is int:
            child = list(self.node)[0]
            for i in range(result):
                xml_gen.parse_node(child, params=self.params)
        elif result is not None:
            logging.error("OneOrMore should return an int, but %s found",
                          type(result))

        return self.cont, None

    @definable
    def numa_cnt(self):
        max_vcpu = self.get_max_vcpu()
        return utils_random.integer(1, max_vcpu)


class ProcessChoice(ProcessBase):

    def process(self, func_name, node, xml_path, node_path, params):
        self.choices = []
        super(ProcessChoice, self).process(
            func_name, node, xml_path, node_path, params)

        if not self.choices:
            return self.cont, None

        choice = random.choice(self.choices)
        return self.cont, xml_gen.parse_node(choice, params=self.params)

    @definable
    def seclabel(self):
        labels = self.xml.findall('./devices//seclabel')
        if not len(labels):
            return self.go_on()

        for label_type in self.node.getchildren():
            type_name_xml = label_type.find(".//attribute[@name='type']/value")
            if type_name_xml is None:
                if label_type.text == 'no':
                    continue
            else:
                type_name = type_name_xml.text
                if type_name == 'none':
                    continue

            self.choices.append(label_type)

    @definable
    def char_type(self):
        if len(self.node.findall('./value')) < 10:
            return self.go_on()

        for val in self.node.getchildren():
            if val.text != 'spicevmc':
                self.choices.append(val)

    @definable
    def input_bus(self):
        value = self.node.find('./value')
        if value is None:
            return self.go_on()
        if value.text != 'ps2':
            return self.go_on()

        if self.cur_xml.get('type') != 'tablet':
            return self.go_on()

        for val in self.node.getchildren():
            if val.text != 'ps2':
                self.choices.append(val)

    @definable
    def input_address(self):
        if self.parent.get('bus') != 'usb':
            return self.go_on()

        for addr in self.node.getchildren():
            add_type = addr.find('./attribute/value').text
            if add_type == 'usb':
                self.choices.append(addr)

    @definable
    def channel_target(self):
        if self.node.find('./ref[@name="virtioTarget"]') is None:
            return self.go_on()
        channel_type = self.cur_xml.get('type')
        if channel_type != 'spicevmc':
            return self.go_on()

        self.choices.append(self.node.find('./ref[@name="virtioTarget"]'))

    @definable
    def char_target(self):
        if self.node.find(
                './optional/ref[@name="qemucdevConsoleTgtType"]') is None:
            return self.go_on()
        tag = self.parent.tag
        if tag == 'serial':
            choice = self.node.find(
                './optional/ref[@name="qemucdevSerialTgtType"]/..')
        elif tag == 'console':
            choice = self.node.find(
                './optional/ref[@name="qemucdevConsoleTgtType"]/..')
        else:
            return self.go_on()
        self.choices.append(choice)

    @definable
    def listen_type(self):
        if self.node.find('./group/attribute[@name="type"]/value') is None:
            return self.go_on()

        if self.parent.get('listen') is None:
            return self.go_on()

        if len(self.parent.findall('./listen')) > 1:
            return self.go_on()

        for listen_type in self.node.getchildren():
            type_name = listen_type.find(
                './attribute[@name="type"]/value').text
            if type_name == 'address':
                self.choices.append(listen_type)

    @definable
    def hostdev_mode(self):
        if self.xml.get('type') not in ['qemu', 'kvm']:
            return self.go_on()

        if self.node.find('./group/ref[@name="hostdevcaps"]') is None:
            return self.go_on()

        for mode in self.node.getchildren():
            mode_type = mode.find('./ref').get('name')
            if mode_type != 'hostdevcaps':
                self.choices.append(mode)

    @definable
    def hostdev_address(self):
        if self.node.find('./group/attribute/value') is None:
            return self.go_on()

        if self.parent.get('type') != 'pci':
            return self.go_on()

        for addr in self.node.getchildren():
            add_type = addr.find('./attribute/value').text
            if add_type == 'pci':
                self.choices.append(addr)

    @definable
    def pci_address(self):
        if self.node.find('./group/attribute/value') is None:
            return self.go_on()

        for addr in self.node.getchildren():
            add_type = addr.find('./attribute/value').text
            if add_type == 'pci':
                self.choices.append(addr)

    @definable
    def redirdev_address(self):
        for addr in self.node.getchildren():
            add_type = addr.find('./attribute/value').text
            if add_type == 'usb':
                self.choices.append(addr)

    @definable
    def controller_model(self):
        value = self.node.find('./value')
        if value is None:
            return self.go_on()

        if value.text != 'pci-root':
            return self.go_on()

        addr = self.cur_xml.find('./address')
        self.cur_xml.remove(addr)
        self.cur_xml.set('index', '0')

        expect_type = None
        if self.xml.find("./devices//address[@type='pci']") is not None:
            expect_type = 'pci-root'
        if self.xml.find("./devices/controller"
                         "[@model='dmi-to-pci-bridge']") is not None:
            expect_type = 'pcie-root'

        for val in self.node.getchildren():
            if expect_type is None:
                self.choices.append(val)
            else:
                if val.text == expect_type:
                    self.choices.append(val)
                    break

    @definable
    def serial_address(self):
        if self.node.find('./group/attribute/value') is None:
            return self.go_on()

        if self.parent.find('./target[@type="usb-serial"]') is None:
            return self.go_on()

        for addr in self.node.getchildren():
            add_type = addr.find('./attribute/value').text
            if add_type == 'usb':
                self.choices.append(addr)

    @definable
    def disk_address(self):
        if self.node.find('./group/attribute/value') is None:
            return self.go_on()

        if self.parent.find('./target[@bus="virtio"]') is None:
            return self.go_on()

        for addr in self.node.getchildren():
            add_type = addr.find('./attribute/value').text
            if add_type == 'pci':
                self.choices.append(addr)

    @definable
    def disk_source(self):
        if self.parent.get('type') in ['floppy', 'cdrom']:
            return self.go_on()

        for val in self.node.getchildren():
            if val.text != 'requisite':
                self.choices.append(val)

    @definable
    def address_family(self):
        family = self.cur_xml.get('family')
        if family not in ['ipv4', 'ipv6']:
            address = self.cur_xml.get('address')
            if address is None:
                family = random.choice(['ipv4', 'ipv6'])
            else:
                if ':' in address:
                    family = 'ipv6'
                else:
                    family = 'ipv4'

        self.choices.append(self.node.find('./ref[@name="%sAddr"]' % family))

    @definable
    def cipher_name(self):
        ciphers = self.parent.findall('./cipher')
        existing_ciphers = set()
        for cipher in ciphers:
            name = cipher.get('name')
            if name is not None:
                existing_ciphers.add(name)

        for val in self.node.getchildren():
            if val.text not in existing_ciphers:
                self.choices.append(val)
