
// This code initializes existing buttons with loadCzml function. Once clicked, the buttons will load specified CZML files.
//
// Usage:
// 1. Add a button with button-czml-load class and data-file property point to the CZML file name you want to load, e.g.
//     <button class="cesium-button button-czml-load" data-file="czml/polish.czml">Polskie satelity</button>
// 2. Call czmlViewer(viewer); from your .ts file.
// 3. Now when user clicks the button, the specified CZML file will be loaded.

import * as Cesium from "cesium";

export function czmlViewer(viewer: Cesium.Viewer) {

    // This updates constellation buttons
    const czmlButtons = [...document.querySelectorAll(".button-czml-load")] as HTMLButtonElement[];
    czmlButtons.forEach(btn => {
        const f = btn.dataset["file"] as string;

        btn.onclick = () => loadCzml(viewer, f);
    });

    // Find all clear-all buttons
    const clearButtons = [...document.querySelectorAll(".button-clear-all")] as HTMLButtonElement[];
    clearButtons.forEach(btn => {
        btn.onclick = () => {
            viewer.dataSources.removeAll();
        }
    })
}

function loadCzml(viewer: Cesium.Viewer, czml: string) {
    var czmlDataSource = new Cesium.CzmlDataSource();
    viewer.dataSources.add(czmlDataSource);
    czmlDataSource.load(czml);
}
