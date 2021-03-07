// This code allows changing inertial or fixed frame of reference.
//
// This code is roughly based on the solution provided by emackey here:
// https://stackoverflow.com/questions/50682925/cesium-earth-show-satellites-in-eci-coordinate-system

// To use this code:
// 1. insert a button of class button-frame-selector, e.g. <button class="cesium-button button-frame-selector" data-names="Stały,Inercjalny">Układ odniesienia</button>
// 2. call referenceFrameSelector(viewer);

import * as Cesium from "cesium";

var fixed_frame: boolean = false;

// Callback function that's called after every postUpdate. Its purpose is to rotate the camera position
// if the fixed_fame is true.
function icrf(scene: Cesium.Scene, time: Cesium.JulianDate) {
    if (scene.mode !== Cesium.SceneMode.SCENE3D) {
        return;
    }

    if (!fixed_frame) {
        return;
    }

    var icrfToFixed = Cesium.Transforms.computeIcrfToFixedMatrix(time);
    if (Cesium.defined(icrfToFixed)) {
        var camera = scene.camera;
        var offset = Cesium.Cartesian3.clone(camera.position);
        var transform = Cesium.Matrix4.fromRotationTranslation(icrfToFixed);
        camera.lookAtTransform(transform, offset);
    }
}

// Calling this function will change the reference frame between intertial and fixed. It actually only
// flips the value of fixed_frame and updates the buttons, the actual magic happens in icrf function.
function flipReferenceFrame() {
    fixed_frame = ! fixed_frame;

    const frameButtons = [...document.querySelectorAll(".button-frame-selector")] as HTMLButtonElement[];
    frameButtons.forEach(btn => {
        const f = btn.dataset["names"] as string;
        var split = f.split(",");
        var prefix = btn.innerText.split(":")[0];
        if (fixed_frame) {
            btn.innerText = prefix + ": " + split[0];
        } else {
            btn.innerText = prefix + ": " + split[1];
        }

    });
}

// This function is expected to be called once, to initialize the reference_frame system.
// todo: the remover callback can be called to remove the callback.
export function referenceFrameSelector(viewer: Cesium.Viewer): void {

    // This updates constellation buttons
    const frameButtons = [...document.querySelectorAll(".button-frame-selector")] as HTMLButtonElement[];
    frameButtons.forEach(btn => {
        const f = btn.dataset["names"] as string;

        btn.onclick = () => flipReferenceFrame();
    });

    const remover = viewer.scene.postUpdate.addEventListener(icrf);
}
