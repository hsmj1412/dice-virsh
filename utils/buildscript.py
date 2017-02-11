import sys
import os


def test(sub, opt):
    mod = sys.modules['dice-virsh_utils.virsh']
    mod.ttt()


def dir_prove():
    wd = os.getcwd()
    wd = os.path.join(wd, 'oracles', 'args')
    if not os.path.isdir(wd):
        os.mkdir(wd)
    return wd


def arg_generate(fp, sub, opt):
    virsh_mod = sys.modules['dice-virsh_utils.virsh']
    argtype = virsh_mod.argtype(sub, opt)
    opt = str(opt) + '_arg'
    opt = opt.replace('-', '_')

    fp.write('- name: ' + opt + '\n')
    fp.write('  depends_on: ' + opt + '\n')
    fp.write('  oracle: |' + '\n')

    if argtype == 'bool':
        fp.write('      return SUCCESS()' + '\n')
    elif argtype == 'nnumber' or argtype == 'time':
        fp.write('      if ' + opt + ' is Integer:' + '\n')
        fp.write('          if ' + opt + ' in virsh.' + argtype + '():' + '\n')
        fp.write('              return SUCCESS()' + '\n')
        fp.write('          else:' + '\n')
        fp.write('              return FAIL()' + '\n')
    elif argtype == 'nstring':
        fp.write('      if ' + opt + ' is String:' + '\n')
        fp.write('          if ' + opt + ' in virsh.' + argtype + '():' + '\n')
        fp.write('              return SUCCESS()' + '\n')
        fp.write('          else:' + '\n')
        fp.write('              return FAIL()' + '\n')
    elif argtype == 'stringlist':
        fp.write('      if ' + opt + ' is StringList:' + '\n')
        fp.write('          if all(' + opt + ' in virsh.' + argtype + '()):' + '\n')
        fp.write('              return SUCCESS()' + '\n')
        fp.write('          else:' + '\n')
        fp.write('              return FAIL()' + '\n')
    fp.write('\n')


def arg_build(sub, opts):
    if opts is None or opts == []:
        return
    wd = os.path.join(dir_prove(), 'args.yaml')
    with open(wd, 'a') as fp:
        for opt in opts:
            arg_generate(fp, sub, opt)



