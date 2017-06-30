from dice.core import item
from dice import utils
import re

DICE_SIGNATURE = 'JunLi'


class Item(item.ItemBase):
    def run(self):
        def replacexml(self, xml=None):
            fs = open(xml, 'r').read()
            xmlreq = re.findall('"(' + DICE_SIGNATURE + '.+?_.+?)"', fs)
            for req in xmlreq:
                if req is not None:
                    reqvalue = utils.escape(str(self.get(req)))
                    fs = fs.replace(req, reqvalue)

            open(xml, 'w').write(fs)

        cmdline = 'virsh'
        cmd = utils.escape(str(self.get('subcmd')))
        cmdline += ' %s' % cmd

        options = self.get('options')
        if options is not None:
            for opt in options:
                cmdline += ' --%s' % utils.escape(str(opt))
                opt = str(opt) + '_arg'
                opt = opt.replace('-', '_')
                arg = self.get(opt)

                if arg is None:
                    arg = ''
                arg = utils.escape(str(arg))
                if re.search('\.xml', arg):
                    replacexml(self, arg)
                cmdline += ' %s' % arg
        f = open('runlog', 'a')
        f.write(cmdline + '\n')
        f.close()
        self.res = utils.run(cmdline)
