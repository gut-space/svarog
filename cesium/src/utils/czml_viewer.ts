
// This code initializes existing buttons with loadCzml function. Once clicked, the buttons will load specified CZML files.
//
// Usage:
// 1. Add a button with button-czml-load class and data-file property point to the CZML file name you want to load, e.g.
//     <button class="cesium-button button-czml-load" data-file="czml/polish.czml">Polskie satelity</button>
// 2. Call czmlViewer(viewer); from your .ts file.
// 3. Now when user clicks the button, the specified CZML file will be loaded.

import * as Cesium from "cesium";

const CZML_URL = 'http://localhost:8080/czml/obs/';

export function czmlViewer(viewer: Cesium.Viewer) {

    // This updates the CZML load buttons
    const czmlButtons = [...document.querySelectorAll(".button-czml-load")] as HTMLButtonElement[];
    czmlButtons.forEach(btn => {
        const f = btn.dataset["file"] as string;

        btn.onclick = () => loadCzml(viewer, f);
    });

    // This adds load observation onclick callback to Show observation
    const czmlLoad = document.getElementById("load-obs") as HTMLButtonElement;
    czmlLoad.onclick = () => {
        let obs_id = (document.getElementById("obs-id") as HTMLInputElement).value;
        loadCzml(viewer, CZML_URL + obs_id);
    };

    // Find the clear button and set the callback to clear all datasources (remove all loaded observations)
    const clearButton = document.getElementById("clear") as HTMLButtonElement;
    if (clearButton) {
        clearButton.onclick = () => {
            viewer.dataSources.removeAll();
        };
    }

    // Find if there's observation number passed in URL. If there is, load the CZML file.
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    if (urlParams.has('obs_id')) {
        console.log("Loading observation " + urlParams.get('obs_id'));
        loadCzml(viewer, CZML_URL + urlParams.get('obs_id'));

        // Also set up the input field to the observation id we just loaded.
        const obs_id = document.getElementById("obs-id") as HTMLInputElement;
        obs_id.value = urlParams.get('obs_id') as string;
    }
}

function loadCzml(viewer: Cesium.Viewer, czml: string) {
    var czmlDataSource = new Cesium.CzmlDataSource();
    viewer.dataSources.add(czmlDataSource);
    czmlDataSource.load(czml);
}
