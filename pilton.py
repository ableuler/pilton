
import sys,os
import subprocess
import re
import bcolors
import tempfile

print os.environ['PFILES']

excecution_root=None

class par:
    def __init__(self,value=None,parline=None):
        if parline is not None:
            self.fromparline(parline)
        
        if isinstance(value,parvalue):
            self.value=value
        
        if value is not None:
            self.value=parvalue(value)
        
    
    def fromparline(self,parline):
        #print parline
        quoted=re.findall("\".*?\"",parline)
        sub=re.sub("\".*?\"","{quoted}",parline)
        #print sub,quoted

        m=re.findall("^(.*?),(.*?),(.*?),(.*?),(.*?),(.*?),\"?(.*)\"?",sub)

        m[0]=[_m.strip() for _m in m[0]]
        for field in 'name','type','mode','default','min','max','prompt':
            f=m[0][0]
            if f=='{quoted}':
                f=quoted[0]
                del quoted[0]
            del m[0][0]
            setattr(self,field,f)

        self.default=re.sub("\"","",self.default)
        if self.type=='i':
            self.default=intvalue(self.default)
        
        if self.type=='a':
            self.default=parvalue(self.default)

        self.value=self.default
        return self.name


    def mkarg(self):
        return "%s=%s"%(self.name,str(self.value))
    
    def __repr__(self):
        return bcolors.render("{BLUE}%s{/} == {YEL}%s{/} (%s)"%(self.name,repr(self.value),self.prompt))

class parvalue:
    def __init__(self,value):
        self.value=value
    
    def formatvalue(self):
        if self.type=="i":
            return "%i"%int(self.value)
        return str(self.value)
    
    def previewvalue(self):
        return str(self.value)

    def __str__(self):
        return self.formatvalue()
    
    def __repr__(self):
        return self.previewvalue()

class intvalue(parvalue):
    def formatvalue(self):
        try:
            return "%i"%int(self.value)
        except ValueError:
            return str(self.value)

class idx(parvalue):
    def __init__(self,idx):
        self.value=idx

    def idx2file(self):
        (file,name)=tempfile.mkstemp()
        file=open(name,"w")
        for i in self.value:
            file.write(i+"\n")
        file.close()
        return name
        
    def formatvalue(self):
        return self.idx2file()


def findafile(path,filename,first=True):
    files=[]
    #print path,filename
    for dir in path:
        cpath=dir+"/"+filename
        if os.path.isfile(cpath):
            if first:
                return cpath
            else:
                files.append(cpath)
    if first or files==[]:
        return None
    return files

class pars:
    def __init__(self):
        self.pars=[]

    def fromparfile(self,parfilename):
        print "from parfile:",parfilename
        for line in open(self.pfile):
            if not re.match("^#",line) and line!="":
                try:
                    p=par(parline=line)
                    self.pars.append(p)
                    print "new par",p
                except Exception as ex:
                    print ex.args
                

    def findparfile(self,toolname,onlysys=False):
        # implementation of the procedure descibed in ... except for the time
        pfiles=os.environ["PFILES"].split(";");

        usr_pfiles=os.environ["PFILES"].split(";")[0].split(":");
        if len(pfiles)==2:
            sys_pfiles=os.environ["PFILES"].split(";")[1].split(":");
        else:
            sys_pfiles=[]

        usrpfile=findafile(usr_pfiles,toolname+".par")
        syspfile=findafile(sys_pfiles,toolname+".par")


        if usrpfile is not None and not onlysys:
            self.pfile=usrpfile
            return self.pfile
        
        if syspfile is not None:
            self.pfile=syspfile
            return self.pfile

        self.pfile=None
        raise Exception("no parfile!")

    def mkargs(self):
        return [par.mkarg() for par in self.pars]
        
    def fromtoolname(self,toolname,onlysys=False):
        self.fromparfile(self.findparfile(toolname,onlysys=onlysys))

    def __getitem__(self,name):
        return filter(lambda x:x.name==name,self.pars)[0]
    
    def __setitem__(self,name,val):
        p=filter(lambda x:x.name==name,self.pars)
        p[0].value=val

    def __repr__(self):
        return  "  "+reduce(lambda x,y:x+"\n  "+y,[repr(p) for p in self.pars])

class HEAToolException(Exception):
    def __init__(self,toolname,code):
        self.toolname=toolname
        self.code=code

    def __str__(self):
        return "HEAtool "+self.toolname+" failed with %i"%self.code

class heatool:
    def __init__(self,toolname,wd=None,onlysyspar=False,env=None,envup={},**args):
        self.toolname=toolname
        self.onlysyspar=onlysyspar

        if env is None: env=os.environ
        if envup is not None: env.update(envup)
        self.environ=env

        self.getpars()
        self.cwd=os.getcwd() if wd is None else wd
        for arg in args:
            self.pars[arg]=args[arg]

    def getpars(self):
        ps=pars()
        ps.fromtoolname(self.toolname,onlysys=self.onlysyspar)
        self.pars=ps
    
    def __getitem__(self,name):
        return self.pars[name]
    
    def __setitem__(self,name,val):
        self.pars[name]=val
    
    def run(self,pretend=False,env=None):
        print bcolors.render("{YEL} work dir to "+self.cwd+"{/}")
        owd=get_cwd()
        os.chdir(self.cwd)

        print bcolors.render("{YEL}"+str([self.toolname]+self.pars.mkargs())+"{/}")
        print bcolors.render("{YEL}"+" ".join([self.toolname]+self.pars.mkargs())+"{/}")
        if pretend:
            print "not actually running it"
            return
        if env is None: env=self.environ
        pr=subprocess.Popen([self.toolname]+self.pars.mkargs(),env=env)
        pr.wait()

        os.chdir(owd)
        if pr.returncode!=0:
            raise HEAToolException(self.toolname,pr.returncode)
        
        return

    def __repr__(self):
        return bcolors.render("{GREEN}%s{/}:\n"%self.toolname)+repr(self.pars)


class og_create(heatool):
    def __init__(self,analysis=None,**args):
        self.osa_analysis=osa_analysis
        heatool.__init__(self,'og_create',**args)

    def run(self,cleanit=True,pretend=False):
        if not pretend:
            os.system("mkdir -p %s"%self['baseDir'].value)
            os.system("ln -sv /isdc/arc/rev_2/scw %s/"%self['baseDir'].value)
            os.system("ln -sv /isdc/arc/rev_2/aux %s/"%self['baseDir'].value)
            os.system("ln -sv /isdc/arc/rev_2/ic %s/"%self['baseDir'].value)
            os.system("ln -sv /isdc/arc/rev_2/idx %s/"%self['baseDir'].value)
            os.system("ln -sv /isdc/arc/rev_2/cat %s/"%self['baseDir'].value)
            if cleanit:
                #if self["%s/%s/%s"%(self['baseDir',])]
                os.system("rm -vrf %s/obs/%s"%(self['baseDir'].value,self.pars['ogid']))
                os.system("rm -vrf %s/obs"%self['baseDir'].value)
            self.osa_analysis.ogdir=str(self['baseDir'].value)+"/obs/"+str(self.pars['ogid'].value)+"/"
        heatool.run(self,pretend)

class ibis_science_analysis(heatool):
    def __init__(self,analysis=None,**args):
        self.osa_analysis=osa_analysis
        heatool.__init__(self,'ibis_science_analysis',**args)

    def run(self,cleanit=True,pretend=False):
        if not pretend:
            os.chdir(self.osa_analysis.ogdir)
        heatool.run(self,pretend)

class osa_analysis:
    def __init__(self,ogid,rep_base_prod):
        self.rep_base_prod=rep_base_prod
        self.commands=[]
        os.environ['COMMONSCRIPT']="1"
        os.environ['COMMONSLOGFILE']="commonlog.txt"

    def og_create(self,**args):
        _og_create=og_create(self,**args)
        self.commands.append(_og_create)
        _og_create.run()
    
    def ibis_science_analysis(self,**args):
        _cmd=ibis_science_analysis(self,**args)
        self.commands.append(_cmd)
        _cmd.run()
        

def get_cwd():
    tf=tempfile.NamedTemporaryFile()
    ppw=subprocess.Popen(["pwd"],stdout=tf)
    ppw.wait()

    try:
        ppw.terminate()
    except OSError:
        pass
    tf.seek(0)
    owd=tf.read()[:-1]
    print "old pwd gives me",owd
    tf.close()
    del tf
    return owd
