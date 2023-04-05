
#ifndef mso5000_h
#define mso5000_h

#include <atomic>

#include "TGraph.h"
#include "TH1D.h"

class mso5000 {

  public:

    mso5000();

    void start(const char *dev="/dev/usbtmc0");
    void stop();

    void set_max_nev(long n) { max_nev = n; }

    void set_tmin(int t) { std::atomic_store(tmin, t); }
    void set_tmax(int t) { std::atomic_store(tmax, t); }

    void set_threshold(int t) { std::atomic_store(threshold, t); }

    void set_adc_sum_bins(int nbins, double min, double max);

    bool get_daq_active() { return daq_active; }

    void draw_shape(const char *opt="lsame") { gpulse_shape.Draw(opt); }
    void draw_adc_sum() { adc_sum.Draw(); }

    int get_tmin() { return std::atomic_load(tmin); }
    int get_tmax() { return std::atomic_load(tmax); }

    int get_threshold() { return std::atomic_load(threshold); }

    double get_capture_rate() { return capture_rate; }

    double get_adc_sum_entries() { return adc_sum.GetEntries(); }
    double get_adc_sum_underflow() { return adc_sum.GetBinContent(0); }
    double get_adc_sum_overflow() { return adc_sum.GetBinContent(adc_sum.GetNbinsX()+1); }
    void write_adc_sum() { adc_sum.Write("adc_sum"); }

  private:

    void read_loop();

    long max_nev; // maximum number of events of nonzero

    std::string device_name; // scope device in /dev

    std::atomic_flag *keep_read; // reading flag

    std::atomic_int *tmin; // minimum time for pulse selection, time bin
    std::atomic_int *tmax; // maximum time for pulse selection, time bin

    std::atomic_int *threshold; // threshold for pulse selection, ADC units

    static TGraph gpulse_shape; // current pulse shape
    static TH1D adc_sum; // ADC sum distribution

    static double capture_rate; // rate of data reads from the scope

    static bool daq_active; // flag for daq activity

};

#endif

