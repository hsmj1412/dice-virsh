import sys
import os
import re

DICE_SIGNATURE = 'JunLi'


def dir_prove():
    wd = os.getcwd()
    wd = os.path.join(wd, 'oracles', 'args')
    if not os.path.isdir(wd):
        os.mkdir(wd)
    return wd


def arg_generate(fp, sub, options):
    opts = options[:]
    virsh_mod = sys.modules['dice-virsh_utils.virsh']
    temp = None
    poolarg = None
    for opt in opts:
        if re.match('string_volname', virsh_mod.argtype(sub, opt)):
            temp = opt
            opts.remove(opt)
            break
    for opt in opts:
        argtype = virsh_mod.argtype(sub, opt)
        opt = str(opt) + '_arg'
        opt = opt.replace('-', '_')

        fp.write('- name: ' + opt + '\n')
        fp.write('  depends_on: ' + opt + '\n')
        fp.write('  oracle: |' + '\n')

        if re.match('bool', argtype):
            fp.write('      return SUCCESS()' + '\n')
        elif re.match('number', argtype):
            fp.write('      if ' + opt + ' is Integer:' + '\n')
            fp.write('          if ' + opt + ' in virsh.' + argtype + '():' +
                     '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        elif re.match('string_xml', argtype):
            fp.write('      if ' + opt + ' is Xml:' + '\n')
            fp.write('          if ' + opt + ' base virsh.' + argtype +
                     '_base():' + '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        elif re.match('string', argtype):
            if re.search('poolname', argtype) and temp:
                poolarg = opt
            fp.write('      if ' + opt + ' is String:' + '\n')
            fp.write('          if ' + opt + ' in virsh.' + argtype + '():' +
                     '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        elif re.match('list', argtype):
            fp.write('      if ' + opt + ' is StringList:' + '\n')
            fp.write('          if all(' + opt + ' in virsh.' + argtype +
                     '()):' + '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        fp.write('\n')
    if temp:
        argtype = virsh_mod.argtype(sub, temp)
        temp = str(temp) + '_arg'
        temp = temp.replace('-', '_')

        fp.write('- name: ' + temp + '\n')
        fp.write('  depends_on: ' + temp + '\n')
        if poolarg is not None:
            fp.write('  require: ' + poolarg + ' is SUCCESS\n')
        fp.write('  oracle: |' + '\n')

        fp.write('      if ' + temp + ' is String:' + '\n')
        if poolarg is None:
            fp.write('          if ' + temp + ' in virsh.' + argtype + '():' +
                     '\n')
        else:
            fp.write('          if ' + temp + ' in virsh.' + argtype + '(' +
                     poolarg + '):' + '\n')
        fp.write('              return SUCCESS()' + '\n')
        fp.write('          else:' + '\n')
        fp.write('              return FAIL()' + '\n')


def arg_build(sub, opts):
    if opts is None or opts == []:
        return
    wd = os.path.join(dir_prove(), 'args.yaml')
    with open(wd, 'a') as fp:
        arg_generate(fp, sub, opts)


def xmlarg_generate(fp=None, xmlreq=[]):
    for nd in xmlreq:
        fp.write('- name: ' + nd[0] + '\n')
        fp.write('  depends_on: ' + nd[0] + '\n')
        fp.write('  oracle: |' + '\n')
        if nd[1] in CPU_COUNT:
            fp.write('      if ' + nd[0] + ' is Integer:' + '\n')
            fp.write('          if ' + nd[0] + ' in virsh.cpu_count():' +
                     '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        elif nd[1] in CPU_LIST:
            fp.write('      if ' + nd[0] + ' is StringList:' + '\n')
            fp.write('          if ' + nd[0] + ' in virsh.cpu_list():' +
                     '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        elif nd[1] in MEMORY:
            fp.write('      if ' + nd[0] + ' is Integer:' + '\n')
            fp.write('          if ' + nd[0] + ' in virsh.memory():' +
                     '\n')
            fp.write('              return SUCCESS()' + '\n')
            fp.write('          else:' + '\n')
            fp.write('              return FAIL()' + '\n')
        fp.write('\n')


def xml_complete(xmlfile):
    xmlstr = open(xmlfile, 'r').read()
    xmlreq = re.findall('"(' + DICE_SIGNATURE + '.+?_(.+?))"', xmlstr)
    wd = os.path.join(dir_prove(), 'xmlargs.yaml')
    with open(wd, 'a') as fp:
        xmlarg_generate(fp, xmlreq)
