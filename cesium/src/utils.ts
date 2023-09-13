import { GroundStation, StationName } from "./model";


function getVisibleValue(shouldVisible: boolean | undefined): boolean | undefined {
    if (typeof shouldVisible === 'undefined') {
        return true;
    }
    // This code alternates between undefined and false. If the property is not
    // defined, Cesium by default shows the object.
    if (!shouldVisible) {
        return false;
    } else {
        return undefined;
    }
}

// This function formats a Date. Right now it only displays HH:MM format
// (and adds leading zeros if needed).
function formatDate(x: Date): string {
    // It was suggested to use toLocaleTimeString(), but there are several problems with that.
    // First, the toLocaleTimeString itself is supported by every major browser, but the various
    // capabilities behind it are not. See https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toLocaleDateString#Browser_compatibility
    // Second, we don't want o have local specific formatting. We want specific HH:MM format that
    // is used around the world on every airport. Third, we don't need the locale-dependent complexity,
    // just show the basic info. We want the flights info panel to be as minimalistic as possible.
    var s: string = "";
    if (x.getHours() < 10)
        s += "0";
    s += x.getHours().toString();
    s += ':';
    if (x.getMinutes() < 10)
        s += "0";
    s += x.getMinutes().toString();

    return s;
}


