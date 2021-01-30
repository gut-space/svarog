#!/bin/bash
# See: https://www.reddit.com/r/RTLSDR/comments/abn29d/automatic_meteor_m2_reception_on_linux_using_rtl/ed2teuv/
# Meteor-M 2 satellite reception

# Arguments
# 1: Prefix path. All path created by this script will be start with it
# 2: Freqency. Value can be specified as an integer (89100000), a float (89.1e6) or as a metric suffix (89.1M).
# 3: Recording duration in seconds

# Returns
# Print on stdout in format:
#	!! CATEGORY: PATH
# where CATEGORY is label, tag, category of file and PATH is path to this file.
# Caller is responsible for returned paths.

if test "$#" -ne 3; then
    echo "ERROR: Expected exactly 3 parameters: BASENAME FREQUENCY RECEIVE_TIMEOUT"
    echo "ERROR: See comment in $0 for details."
    exit 1
fi

BASENAME=$1
FREQUENCY=$2
RECEIVE_TIMEOUT=$3

NORMALIZED_SIGNAL_FILENAME=${BASENAME}_normalized_signal.wav
QPSK_FILENAME=${BASENAME}_qpsk.qpsk
DUMP_PREFIX_FILENAME=${BASENAME}_dump
PRODUCT_FILENAME_WITOUT_EXT=${BASENAME}_product
PRODUCT_BITMAP_FILENAME=${PRODUCT_FILENAME_WITOUT_EXT}.bmp

SIGNAL_FILENAME=${BASENAME}_signal.wav
PRODUCT_FILENAME=${PRODUCT_FILENAME_WITOUT_EXT}.png

# This little function checks if meteor demod is available as meteor_demod or meteor-demod
# and then sets the $METEOR_DEMOD variable accordingly.
meteor_demod_name() {

    # command -v is really a portable which command
    command -v meteor-demod > /dev/null
    if test "$?" -eq 0; then
        METEOR_DEMOD="meteor-demod"
        return
    fi

    command -v meteor_demod > /dev/null
    if test "$?" -eq 0; then
        METEOR_DEMOD="meteor_demod"
        return
    fi

    echo "ERROR: meteor-demod not found. Couldn't find meteor-demod nor meteor_demod."
    echo "ERROR: Make sure those are available in the system PATH."
    exit 1
}

meteor_demod_name
echo "METEOR DEMOD found: [$METEOR_DEMOD]"

$METEOR_DEMOD

# Record raw IQ data
timeout "$RECEIVE_TIMEOUT" \
    rtl_fm -M raw -f "$FREQUENCY" -s 288k -g 48 -p 1 | \
    sox -t raw -r 288k -c 2 -b 16 -e s - -t wav "$SIGNAL_FILENAME" rate 96k

retVal=$?
if [ $retVal -ne 0 ]; then
	exit $retVal
fi


echo "!! Signal: $SIGNAL_FILENAME"
# Normalize .wav
sox "$SIGNAL_FILENAME" "$NORMALIZED_SIGNAL_FILENAME" gain -n || exit $?
echo "Normalized"
# Demodulate .wav to QPSK using meteor-demod
yes | $METEOR_DEMOD -o "$QPSK_FILENAME" -B "$NORMALIZED_SIGNAL_FILENAME" || exit $?
rm "$NORMALIZED_SIGNAL_FILENAME"
echo "Demodulated"
# Keep original file timestamp
touch -r "$SIGNAL_FILENAME" "$QPSK_FILENAME" || exit $?
echo "Touched"
# Decode QPSK
medet "$QPSK_FILENAME" "${DUMP_PREFIX_FILENAME}" -cd || exit $?
rm "$QPSK_FILENAME"
echo "Dumped"
# Generate images
medet "${DUMP_PREFIX_FILENAME}.dec" "$PRODUCT_FILENAME_WITOUT_EXT" -r 68 -g 65 -b 64 -d || exit $?
rm "${DUMP_PREFIX_FILENAME}"*
echo "Decoded"
# Convert to PNG
convert "$PRODUCT_BITMAP_FILENAME" "$PRODUCT_FILENAME" || exit $?
rm "$PRODUCT_BITMAP_FILENAME"
echo "Converted"
echo !! Product: "$PRODUCT_FILENAME"

# Demodulator from: https://github.com/dbdexter-dev/meteor_demod
# Decoder from: https://github.com/artlav/meteor_decoder
# Many Tnx to authors!

# timeout 600: reception time
# if your reception conditions are good, you can use "rate 120k" or more
# /something: replace with your path
# Works on RPi3
