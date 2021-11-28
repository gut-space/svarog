# Submitting observations

This page describes the protocol and parameters necessary for submitting new
observations. It is a work in progress.

## Configuration

Configuration should be submitted as JSON. There's a number of parameters that
are (almost) mandatory:

- protocol - string, e.g. APT, BPSK, HRPT
- frequency - floating, expressed in Hz
- antenna - string, model of the antenna used to receive data. Feel free to specify exact brand and model number
- antenna-type - string, defines type, e.g. yagi, crossed dipole, helix, parabolic etc.
- receiver - string, specifies the model of your SDR (or radio in general), e.g. AirSpy Mini
- lna - string, specifies the Low Noise Amplifier. Please use `none` if you don't use LNA
- filter - string, describe the filter or filters you're using. Please use `none` if you don't use LNA

The structure is flexible, and it's OK to submit additional parameters.
If you define new parameters, please use all lowercase name. Try to be consistent
and don't use abbreviations. The parameter name will be shown as is in the UI.