#!/usr/bin/python3

#_____________________________________________________________________________
#
# Main GUI for the pulse analyser, opens as
#
#  ./run.py
#
# Library to communicate with the scope is expected at ./mso5000/build
#
#_____________________________________________________________________________

from threading import Timer, Thread, Event
from time import sleep

import npyscreen as npy

import ROOT as rt
from ROOT import TEveManager, gEve, gStyle, gPad
from ROOT import TLine, TH1I, TLegend, TFile

import sys
sys.path.append("mso5000/build") # expected location for the .so library
from mso5000 import mso5000

#_____________________________________________________________________________
class gui(npy.NPSAppManaged):

    #_____________________________________________________________________________
    def __init__(self, **kws):
        npy.NPSAppManaged.__init__(self, **kws)

        #online plots
        TEveManager.Create()

        self.can_pulse = gEve.AddCanvasTab("Plots")
        self.can_pulse.Divide(2, 1)

        #scope instance
        self.mso = mso5000()

        #online update loop
        self.update_period = 0.4 # sec
        self.online_running = Event()

        self.busy = False # running flag

    #__init__

    #_____________________________________________________________________________
    def main(self):

        #main frame for the gui
        frame = npy.Form(name="MSO5000 Pulse Analyser", lines=22, columns=85)

        self.registerForm("main", frame)

        #run control
        nav_x = 2
        nav_y = 2
        frame.add(npy.BoxBasic, name="Run Control", editable=False, relx=nav_x, rely=nav_y, width=36, height=7)
        frame.add(npy.ButtonPress, name="Start", when_pressed_function=self.run_start, relx=nav_x+1, rely=nav_y+1)
        frame.add(npy.ButtonPress, name="Stop", when_pressed_function=self.run_stop, relx=nav_x+1, rely=nav_y+2)
        frame.add(npy.ButtonPress, name="Run for events:", when_pressed_function=self.run_max_nev, relx=nav_x+1, rely=nav_y+3)
        self.set_max_nev = frame.add(npy.Textfield, max_width=10, relx=nav_x+21, rely=nav_y+3)
        self.set_max_nev.value = "0"
        self.set_dev_name = frame.add(npy.TitleText, name="Device", max_width=35, begin_entry_at=12, relx=nav_x+1, rely=nav_y+4)
        self.set_dev_name.value = "/dev/usbtmc0"

        #pulse selection
        nav_x = 2
        nav_y = 10
        frame.add(npy.BoxBasic, name="Pulse selection", editable=False, relx=nav_x, rely=nav_y, width=36, height=6)
        self.set_tmin = frame.add(npy.TitleText, name="Tmin (blue)", max_width=35, begin_entry_at=21, relx=nav_x+1, rely=nav_y+1)
        self.set_tmin.value = "0"
        self.set_tmax = frame.add(npy.TitleText, name="Tmax (red)", max_width=35, begin_entry_at=21, relx=nav_x+1, rely=nav_y+2)
        self.set_tmax.value = "1000"
        self.set_threshold = frame.add(npy.TitleText, name="Threshold (green)", max_width=35, begin_entry_at=21,\
            relx=nav_x+1, rely=nav_y+3)
        self.set_threshold.value = "0"

        #ADC sum distribution
        nav_x = 40
        nav_y = 2
        frame.add(npy.BoxBasic, name="ADC sum distribution", editable=False, relx=nav_x, rely=nav_y, width=36, height=6)
        self.set_int_nbins = frame.add(npy.TitleText, name="Num bins", max_width=25, relx=nav_x+1, rely=nav_y+1)
        self.set_int_nbins.value = "1000"
        self.set_int_xmin = frame.add(npy.TitleText, name="ADC min", max_width=25, relx=nav_x+1, rely=nav_y+2)
        self.set_int_xmin.value = "0"
        self.set_int_xmax = frame.add(npy.TitleText, name="ADC max", max_width=25, relx=nav_x+1, rely=nav_y+3)
        self.set_int_xmax.value = "1000"

        #Export
        nav_x = 40
        nav_y = 9
        frame.add(npy.BoxBasic, name="Export", editable=False, relx=nav_x, rely=nav_y, width=36, height=7)
        self.set_out_name = frame.add(npy.TitleText, name="File name", max_width=35, begin_entry_at=12, relx=nav_x+1, rely=nav_y+1)
        self.set_out_name.value = "mso.root"
        frame.add(npy.ButtonPress, name="Save", when_pressed_function=self.run_save, relx=nav_x+1, rely=nav_y+2)

        #clear and start
        npy.blank_terminal()
        frame.edit()

    #main

    #_____________________________________________________________________________
    def run_start(self, max_nev=0):

        #prevent multiple starts
        if self.busy:
            return
        self.busy = True

        #set histograms
        self.mso.set_adc_sum_bins(int(self.set_int_nbins.value), float(self.set_int_xmin.value), float(self.set_int_xmax.value))

        #maximal number of events, nonzero if requested
        self.mso.set_max_nev(max_nev)

        #start daq from the scope
        self.mso.start(self.set_dev_name.value)

        #online monitor
        self.online_running.set()
        otd = Thread(target=self.online_loop)
        otd.start()

    #run_start

    #_____________________________________________________________________________
    def run_max_nev(self):

        #run for maximal number of events

        #test for valid data
        try:
            max_nev_val = int(self.set_max_nev.value)
        except:
            return

        #test for non-zero request
        if max_nev_val <= 0:
            return

        #run with the given number of events
        self.run_start(max_nev_val)

    #run_max_nev

    #_____________________________________________________________________________
    def run_stop(self):

        #stop the daq from the scope
        self.mso.stop()

        #stop the online monitor
        self.online_running.clear()

        self.busy = False

    #run_stop

    #_____________________________________________________________________________
    def run_save(self):

        #save analysis data to the file

        out = TFile(self.set_out_name.value, "recreate")

        self.mso.write_adc_sum()

        out.Close()

    #run_save

    #_____________________________________________________________________________
    def online_loop(self):

        #thread created in  run_start  function

        while True:

            #stop request from the scope
            if not self.mso.get_daq_active():
                self.run_stop()

            #stop requrest from run control
            if not self.online_running.is_set():
                break

            #wait for update period and make the update
            sleep(self.update_period)
            self.online_update()

        #last update after stop
        sleep(self.update_period)
        self.online_update()

    #update_loop

    #_____________________________________________________________________________
    def online_update(self):

        #make the update, called from  online_loop  function

        #input data on pulse selection
        try:
            self.mso.set_tmin(int(self.set_tmin.value))
            self.mso.set_tmax(int(self.set_tmax.value))
            self.mso.set_threshold(int(self.set_threshold.value))
        except:
            pass

        #plot of pulse shape
        gframe = TH1I("gframe", "", 1, 0, 1000)
        gframe.SetMaximum(255)
        gframe.SetXTitle("Time bin")
        gframe.SetYTitle("ADC value")

        self.can_pulse.cd(1)
        gframe.Draw()
        self.mso.draw_shape()
        gPad.SetLeftMargin(0.11)

        #lines representing pulse selection
        tmin = self.mso.get_tmin()
        tmax = self.mso.get_tmax()
        thres = self.mso.get_threshold()

        lmin = TLine(tmin, 0, tmin, 255)
        lmin.SetLineColor(rt.kBlue)
        lmin.Draw("same")

        lmax = TLine(tmax, 0, tmax, 255)
        lmax.SetLineColor(rt.kRed)
        lmax.Draw("same")

        lth = TLine(0, thres, 1000, thres)
        lth.SetLineColor(rt.kGreen)
        lth.Draw("same")

        gleg = TLegend(0.6, 0.82, 0.56, 0.89)
        gleg.SetBorderSize(0)
        gleg.SetTextSize(0.035)
        gleg.AddEntry("", "Samples/sec: {0:.1f}".format(self.mso.get_capture_rate()), "")
        gleg.AddEntry("", "Online: "+str(self.busy), "")
        gleg.Draw("same")

        #plot on ADC sum distribution
        self.can_pulse.cd(2)
        self.mso.draw_adc_sum()

        ileg = TLegend(0.62, 0.8, 0.62, 0.89)
        ileg.SetBorderSize(0)
        ileg.SetTextSize(0.035)
        ileg.AddEntry("", "Entries: "+str(self.mso.get_adc_sum_entries()), "")
        ileg.AddEntry("", "Underflow: "+str(self.mso.get_adc_sum_underflow()), "")
        ileg.AddEntry("", "Overflow: "+str(self.mso.get_adc_sum_overflow()), "")
        ileg.Draw("same")

        self.can_pulse.Update()

    #online_update

#_____________________________________________________________________________
if __name__ == "__main__":

    #clean layout for ROOT plots
    gStyle.SetOptStat("")

    #create the gui
    gui = gui()
    gui.run()

    #stop everything at exit
    gui.run_stop()










