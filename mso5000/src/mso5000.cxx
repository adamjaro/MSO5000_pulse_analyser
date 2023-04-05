
//_____________________________________________________________________________
//
// Class to communicate with the scope, runs the thread for daq
// and performs pulse analysis.
//
//_____________________________________________________________________________

//C
#include <unistd.h>
#include <fcntl.h>

//C++
#include <iostream>
#include <thread>

//local classes
#include "mso5000.h"

using namespace std;

//static members
TGraph mso5000::gpulse_shape;
TH1D mso5000::adc_sum;

double mso5000::capture_rate = 0;
bool mso5000::daq_active = false;

//_____________________________________________________________________________
mso5000::mso5000(): max_nev(0) {

  //reserve 1000 values for pulse shape
  gpulse_shape.Set(1000);

  //ADC sum distribution
  adc_sum.SetName("adc_sum");
  adc_sum.SetXTitle("ADC sum x1000");
  //adc_sum.SetYTitle("Counts");

  //flag for daq loop
  keep_read = new atomic_flag(ATOMIC_FLAG_INIT);

  //time range for pulse selection in time bins
  tmin = new atomic_int(ATOMIC_VAR_INIT(1));
  tmax = new atomic_int(ATOMIC_VAR_INIT(1000));

  //threshold for pulse selection in ADC units
  threshold = new atomic_int(ATOMIC_VAR_INIT(0));

}//mso5000

//_____________________________________________________________________________
void mso5000::set_adc_sum_bins(int nbins, double min, double max) {

  //set bins and range for ADC sum distribution

  adc_sum.SetBins(nbins, min, max);

}//set_adc_sum_bins

//_____________________________________________________________________________
void mso5000::start(const char *dev) {

  //set the device name in /dev
  device_name = dev;

  //set flag for daq loop
  keep_read->test_and_set();

  //run the thread with daq from the scope
  thread mt(&mso5000::read_loop, *this);
  mt.detach();

}//start

//_____________________________________________________________________________
void mso5000::stop() {

  //clear flag to stop the thread with daq
  keep_read->clear();

}//stop

//_____________________________________________________________________________
void mso5000::read_loop() {

  //set active flag for online monitor
  daq_active = true;

  //reset the histograms
  adc_sum.Reset();

  //open connection to the scope
  int fd = open(device_name.c_str(), O_RDWR);
  if( fd < 0 ) {
    daq_active = false;
    return;
  }

  //IO data to communicate with the scope
  char buffer[2048];

  //start time for capture rate
  chrono::system_clock::time_point t0 = chrono::system_clock::now();

  //number of analysed events
  long nev = 0;

  //daq loop
  while(1) {

    //test flag to maintain the loop
    if( !keep_read->test_and_set() ) {
      close(fd);
      break;
    }

    //waveform data
    sprintf(buffer, ":WAV:DATA?");
    write(fd, buffer, strlen(buffer));
    read(fd, buffer, 2048);

    //ADC sum in current event
    double evt_adc_sum = 0;

    //waveform loop
    for(int i=11; i<1011; i++) {

      //pulse time and ADC value
      int time = i - 11; // time bin
      int adc = (unsigned char)(buffer[i]); // ADC value
      //int adc = 121;

      //point in pulse TGraph
      gpulse_shape.SetPoint(time, time, adc);

      //apply the time interval
      if( time < atomic_load(tmin) ) continue;
      if( time > atomic_load(tmax) ) continue;

      //apply the threshold
      int thval = atomic_load(threshold);
      if( adc < thval ) continue;

      //add to the ADC sum, threshold is subtracted
      evt_adc_sum += (adc-thval)*1e-3;

    }//waveform loop

    //fill the histograms
    adc_sum.Fill(evt_adc_sum);

    //increment event count
    nev++;

    //update the capture rate
    chrono::system_clock::time_point t1 = chrono::system_clock::now(); // current time

    chrono::milliseconds dt = chrono::duration_cast<chrono::milliseconds>(t1 - t0); // time since the beginning
    long ldt = dt.count();

    capture_rate = nev/(ldt*1e-3); // rate as events/sec

    //test for maximal number of events if requested
    if(max_nev > 0 and nev >= max_nev) {

      keep_read->clear();
    }

  }//daq loop

  //clear active flag for online monitor
  daq_active = false;

}//read_loop















