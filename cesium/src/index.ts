
import { showCursorLabel } from "./utils/cursor_label";
import { czmlViewer } from "./utils/czml_viewer";
import { referenceFrameSelector } from "./utils/reference_frame";

import * as Cesium from "cesium";

// This is Tomek's private token generated when signed up for Cesium.
// cspell: disable-next-line
Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI4YmI1YmYxNC0xY2Q3LTQ0NjctODU5My04YWIxMDEwOWRkNTgiLCJpZCI6MTY2NTMsInNjb3BlcyI6WyJhc3IiLCJnYyJdLCJpYXQiOjE1NzA4ODgxNTF9.30hjTWZfohYJ4bNOy1DRjCeqhb2ldJ_Vze5uVWeke5Y';

// STEP 0: CREATE CESIUM WIDGET
var rectangle = Cesium.Rectangle.fromDegrees(14,51,21,54);
Cesium.Camera.DEFAULT_VIEW_RECTANGLE = rectangle;
Cesium.Camera.DEFAULT_VIEW_FACTOR = 3;

// This creates the top-level widget for Cesium.
export const viewer = new Cesium.Viewer('cesiumContainer', {
    infoBox : true,
    selectionIndicator : true,
    shadows : true,
    shouldAnimate : true
});

showCursorLabel(viewer);

czmlViewer(viewer);

referenceFrameSelector(viewer);