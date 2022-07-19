from random import Random
from tkinter import *
from tkinter import filedialog
from tkinter import font
from tkinter import messagebox
from idlelib.tooltip import Hovertip
import traceback
from BuildLibs.grp import *

# from https://stackoverflow.com/a/68701602
class ScrollableFrame:
    """
    # How to use class
    from tkinter import *
    obj = ScrollableFrame(master,height=300 # Total required height of canvas,width=400 # Total width of master)
    objframe = obj.frame
    # use objframe as the main window to make widget
    """
    def __init__ (self,master,width,height,mousescroll=0):
        self.mousescroll = mousescroll
        self.master = master
        self.height = height
        self.width = width
        self.main_frame = Frame(self.master)
        self.main_frame.pack(fill=BOTH,expand=1)

        self.scrollbar = Scrollbar(self.main_frame, orient=VERTICAL)
        self.scrollbar.pack(side=RIGHT,fill=Y)

        self.canvas = Canvas(self.main_frame,yscrollcommand=self.scrollbar.set)
        self.canvas.pack(expand=True,fill=BOTH)

        self.scrollbar.config(command=self.canvas.yview)

        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion = self.canvas.bbox("all")))

        self.frame = Frame(self.canvas,width=self.width,height=self.height)
        self.frame.pack(expand=True,fill=BOTH)
        self.canvas.create_window((0,0), window=self.frame, anchor="nw")

        self.frame.bind("<Enter>", self.entered)
        self.frame.bind("<Leave>", self.left)

    def _on_mouse_wheel(self,event):
        self.canvas.yview_scroll(-1 * int((event.delta / 120)), "units")

    def entered(self,event):
        if self.mousescroll:
            self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)

    def left(self,event):
        if self.mousescroll:
            self.canvas.unbind_all("<MouseWheel>")

class RandoSettings:
    def __init__(self):
        self.width=489
        self.height=573
        self.initWindow()
        self.ChooseFile()
        if self.root:
            self.root.mainloop()

    def closeWindow(self):
        self.root.destroy()
        self.root=None

    def isWindowOpen(self) -> bool:
        return self.root!=None

    def resize(self,event):
        if event.widget == self.root:
            try:
                #print('resize', event.width, event.height)
                self.width = event.width
                self.height = event.height
            except Exception as e:
                print('ERROR: in resize:', e)

    def _ChooseFile(self):
        grppath = ''
        try:
            self.randoButton["state"]='disabled'
            self.update()
            grppath = chooseFile(self.root)
            if grppath == '':
                warning('no file selected!')
                self.closeWindow()
                return True

            self.grppath = grppath
            self.root.title('Loading '+grppath+'...')
            self.update()
            self.grp: GrpBase = LoadGrpFile(grppath)

            self.root.title(self.grp.game.type + ' ' + GetVersion() + ' Randomizer - ' + self.grp.game.name)
            self.randoButton["state"]='normal'
            self.update()
        except Exception as e:
            errordialog('Error Opening File', grppath, e)
            self.closeWindow()
            raise
        return True

    def ChooseFile(self):
        self._ChooseFile()
        if not self.isWindowOpen():
            return
        if not self.grp.conSettings.conFiles:
            self.rangeVar.set('Unavailable for this game')
            self.range['state'] = 'disabled'
            self.difficultyVar.set('Unavailable for this game')
            self.difficulty['state'] = 'disabled'
        if not self.grp.mapSettings.addableEnemies:
            self.enemyVarietyVar.set('Unavailable for this game')
            self.enemyVariety['state'] = 'disabled'


    def _Randomize(self):
        seed = self.seedEntry.get()
        if seed == '':
            seed = random.randint(1, 999999)

        settings = {}
        unavail = 'Unavailable for this game'

        settings['MapFile.chanceDupeItem'] = {'Few': 0.3, 'Some': 0.5, 'Many': 0.7, 'Extreme': 0.9}[self.enemiesVar.get()]
        settings['MapFile.chanceDeleteItem'] = {'Few': 0.4, 'Some': 0.3, 'Many': 0.1, 'Extreme': 0.1}[self.enemiesVar.get()]

        settings['MapFile.chanceDupeEnemy'] = {'Few': 0.2, 'Some': 0.5, 'Many': 0.6, 'Extreme': 0.9}[self.enemiesVar.get()]
        settings['MapFile.chanceDeleteEnemy'] = {'Few': 0.5, 'Some': 0.3, 'Many': 0.2, 'Extreme': 0.1}[self.enemiesVar.get()]

        settings['MapFile.itemVariety'] = {'Normal': 0, 'Increased': 0.2, 'Extreme': 0.5, unavail: 0}[self.itemVarietyVar.get()]
        settings['MapFile.enemyVariety'] = {'Normal': 0, 'Increased': 0.2, 'Extreme': 0.5, unavail: 0}[self.enemyVarietyVar.get()]

        settings['conFile.range'] = {'Low': 0.5, 'Medium': 1, 'High': 1.5, 'Extreme': 2.0, unavail: 1}[self.rangeVar.get()]
        settings['conFile.scale'] = 1.0
        settings['conFile.difficulty'] = {'Easy': 0.3, 'Medium': 0.5, 'Difficult': 0.7, 'Extreme': 0.9, unavail: 0.5}[self.difficultyVar.get()]

        settings['grp.reorderMaps'] = {'Disabled': False, 'Enabled': True}[self.reorderMapsVar.get()]

        self.grp.Randomize(seed, settings=settings)
        messagebox.showinfo('Randomization Complete!', 'All done! Seed: ' + str(seed))
        self.closeWindow()

    def WarnOverwrites(self) -> bool:
        deleting = self.grp.GetDeleteFolders(self.grp.GetOutputPath())
        return messagebox.askokcancel(
            title='Will DELETE files!',
            message='This may take a minute.\nWILL DELETE/OVERWRITE THE FOLLOWING:\n'
            + '\n'.join(deleting)
        )

    def Randomize(self):
        try:
            self.randoButton["state"]='disabled'
            self.update()

            if not self.WarnOverwrites():
                info('Declined overwrite warning, not randomizing')
                if self.isWindowOpen():
                    self.randoButton["state"]='normal'
                return

            self._Randomize()
        except Exception as e:
            errordialog('Error Randomizing', self.grppath, e)
            if self.isWindowOpen():
                self.randoButton["state"]='normal'
            raise


    def newInput(self, cls, label:str, tooltip:str, row:int, *args):
        label = Label(self.win,text=label,width=20,height=2,font=self.font, anchor='e', justify='left')
        label.grid(column=0,row=row, sticky='E')
        if cls == OptionMenu:
            entry = cls(self.win, *args)
        else:
            entry = cls(self.win, *args, width=20,font=self.font)
        entry.grid(column=1,row=row, sticky='W')

        myTip = Hovertip(label, tooltip)
        myTip = Hovertip(entry, tooltip)
        return entry

    def initWindow(self):
        self.root = Tk()
        self.root.protocol("WM_DELETE_WINDOW",self.closeWindow)
        self.root.bind("<Configure>",self.resize)
        self.root.title('Build Engine Randomizer '+GetVersion()+' Settings')
        self.root.geometry(str(self.width)+"x"+str(self.height))

        scroll = ScrollableFrame(self.root, width=self.width, height=self.height, mousescroll=1)
        self.win = scroll.frame
        #self.win.config()
        self.font = font.Font(size=14)

        row=0
        infoLabel = Label(self.win,text='Make sure you have a backup of your game files!\nRandomizer might overwrite files\ninside the game directory.',width=40,height=4,font=self.font)
        infoLabel.grid(column=0,row=row,columnspan=2,rowspan=1)
        row+=1

        self.seedEntry = self.newInput(Entry, 'Seed: ', 'RNG Seed', row)
        row+=1

        # items add/reduce? maybe combine them into presets so it's simpler to understand
        self.itemsVar = StringVar(self.win, 'Some')
        items = self.newInput(OptionMenu, 'Items: ', 'How many items.\n"Some" is a similar amount to vanilla.', row, self.itemsVar, 'Few', 'Some', 'Many', 'Extreme')
        row+=1

        # enemies add/reduce?
        self.enemiesVar = StringVar(self.win, 'Some')
        enemies = self.newInput(OptionMenu, 'Enemies: ', 'How many enemies.\n"Some" is a similar amount to vanilla.', row, self.enemiesVar, 'Few', 'Some', 'Many', 'Extreme')
        row+=1

        # values range
        self.rangeVar = StringVar(self.win, 'Medium')
        self.range = self.newInput(OptionMenu, 'Randomization Range: ', 'How wide the range of values can be randomized.\nThis affects the values in CON files.', row, self.rangeVar, 'Low', 'Medium', 'High', 'Extreme')
        row+=1

        # difficulty? values difficulty?
        self.difficultyVar = StringVar(self.win, 'Medium')
        self.difficulty = self.newInput(OptionMenu, 'Difficulty: ', 'Increase the difficulty for more challenge.\nThis affects the values in CON files.', row, self.difficultyVar, 'Easy', 'Medium', 'Difficult', 'Extreme')
        row+=1

        self.itemVarietyVar = StringVar(self.win, 'Normal')
        self.itemVariety = self.newInput(OptionMenu, 'Item Variety: ', 'Chance to add items that shouldn\'t be on the map.', row, self.itemVarietyVar, 'Normal', 'Increased', 'Extreme')
        row+=1

        self.enemyVarietyVar = StringVar(self.win, 'Normal')
        self.enemyVariety = self.newInput(OptionMenu, 'Enemy Variety: ', 'Chance to add enemies that shouldn\'t be on the map.\nThis can create difficult situations.', row, self.enemyVarietyVar, 'Normal', 'Increased', 'Extreme')
        row+=1

        self.reorderMapsVar = StringVar(self.win, 'Disabled')
        reorderMaps = self.newInput(OptionMenu, 'Reorder Maps: ', 'Shuffle the order of the maps.', row, self.reorderMapsVar, 'Disabled', 'Enabled')
        row+=1

        # TODO: option to enable/disable loading external files?
        # TODO: option to enable.disable useRandomizerFolder

        #self.progressbar = Progressbar(self.win, maximum=1)
        #self.progressbar.grid(column=0,row=row,columnspan=2)
        #row+=1

        self.randoButton = Button(self.win,text='Randomize!',width=20,height=2,font=self.font, command=self.Randomize)
        self.randoButton.grid(column=1,row=100, sticky='SE')
        Hovertip(self.randoButton, 'Dew it!')

    def update(self):
        self.root.update()

def main():
    settings = RandoSettings()

def chooseFile(root):
    filetype = (("All Supported Files",("*.grp","STUFF.DAT")), ("GRP File","*.grp"), ("all files","*.*"))
    target = filedialog.askopenfilename(title="Choose a GRP file",filetypes=filetype)
    return target

def errordialog(title, msg, e=None):
    if e:
        msg += '\n' + str(e) + '\n\n' + traceback.format_exc()
    error(title, '\n', msg)
    messagebox.showerror(title, msg)
