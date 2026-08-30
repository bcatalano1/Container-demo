const form = document.getElementById('calculator-form');
const result = document.getElementById('result');
const urlParams = new URLSearchParams(window.location.search);
const authCode = urlParams.get('code');
const adjustedHydration = document.getElementById('adjusted-hydration');
const resultMeta = document.getElementById('result-meta');
const errorMessage = document.getElementById('error-message');
let keyHistory = [null]; //page 1 always start with no bookmarks
let currentPage = 0;
let nextBookmark = null;


async function handleLogin() {
    if (!authCode) {
        console.log('No auth code found in URL.');
        return;
    }

    const tokenUrl = 'https://us-east-1igwrbzve9.auth.us-east-1.amazoncognito.com/oauth2/token';

    const requestBody = new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: '2objbddv7ej2p0gs2g0e68cbad',
        code: authCode,
        redirect_uri: 'http://localhost:3000/app.html'
    });

    try {
        const response = await fetch(tokenUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: requestBody
        });

        if (!response.ok) {
            throw new Error(`Token request failed with status ${response.status}`);
        }

        const tokens = await response.json();
        const payloadString = tokens.id_token.split('.')[1];
        const userData = JSON.parse(atob(payloadString));
        console.log('Access Token:', tokens.access_token);
        console.log("Logged in User ID:", userData.sub);

        // Save the unique ID so we remember them next time
        localStorage.setItem('user_id', userData.sub);
        currentUserId = userData.sub;
        window.history.replaceState({}, document.title, "/app.html");
    }

    catch (error) {
        console.error("Login failed:", error);
    }

}

form.addEventListener('submit', async function (event) {
    event.preventDefault();

    const baseHydration = Number(document.getElementById('base-hydration').value);
    const elevation = Number(document.getElementById('elevation').value);

    errorMessage.textContent = '';
    errorMessage.classList.remove('visible');

    if (!Number.isFinite(baseHydration) || !Number.isFinite(elevation)) {
        errorMessage.textContent = 'Please enter valid numbers for both fields.';
        errorMessage.classList.add('visible');
        return;
    }

    try {
        const response = await fetch('http://localhost:8000/calculate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                base_hydration: baseHydration,
                elevation: elevation,
                user_id: localStorage.getItem('user_id') || null
            }),
        });

        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }

        const data = await response.json();
        const payload = data.body && typeof data.body === 'object' ? data.body : data;

        const finalHydration = Number(payload.final_hydration);

        if (!Number.isFinite(finalHydration)) {
            throw new Error('Invalid hydration response from the server.');
        }

        adjustedHydration.textContent = `${finalHydration.toFixed(2)}%`;
        resultMeta.textContent = `Base hydration: ${Number(payload.base_hydration).toFixed(2)}% • Added water: ${Number(payload.added_water_percentage).toFixed(2)}%`;
        result.classList.add('visible');
        loadRecipes(); // Refresh the list of recipes after a successful calculation
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'Unable to calculate hydration. Please check that the backend is running and try again.';
        errorMessage.classList.add('visible');
        result.classList.remove('visible');
    }
});
async function loadRecipes(startKey = null) {
    let url = 'http://localhost:8000/recipes';
    if (startKey) {
        url += `?start_recipe_id=${encodeURIComponent(startKey)}`;
    }
    try {
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        const data = await response.json();
        console.log("Backend sent this many recipes:", data.items.length);
        console.log("Next bookmark is:", data.next_key);
        //const recipes = await response.json();
        const listElement = document.getElementById('recipes-list');
        listElement.innerHTML = '';
        if (data.items.length === 0) {
            listElement.textContent = 'No recent recipes found.';
            return;
        }
        data.items.forEach(recipe => {
            //const recipeCard = document.createElement('div');
            //recipeCard.textContent = `Recipe ID: ${recipe.recipe_id}, Base Hydration: ${recipe.base_hydration}%, Elevation: ${recipe.elevation} ft, Final Hydration: ${recipe.final_hydration}%`;
            const recipeCard = `
            <div style="border: 1px solid #ccc; padding: 10px; margin-top: 10px;">
                <p><strong>Base Hydration:</strong> ${recipe.base_hydration}%</p>
                <p><strong>Elevation:</strong> ${recipe.elevation} ft</p>
                <p><strong>Added Water:</strong> ${recipe.added_water_percentage}%</p>
                <p><strong>Final Hydration:</strong> ${recipe.final_hydration}%</p>
            </div>
            `;
            //listElement.appendChild(recipeCard);
            listElement.innerHTML += recipeCard;
        });
        // Update pagination buttons
        nextBookmark = data.next_key;
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        // Handle the Previous Button
        if (currentPage === 0) {
            prevBtn.disabled = true;  // We are on page 1, lock the button
        } else {
            prevBtn.disabled = false; // We are on page 2+, unlock the button
        }

        // Handle the Next Button
        if (!nextBookmark) {
            nextBtn.disabled = true;  // No bookmark from AWS = no more recipes, lock it
        } else {
            nextBtn.disabled = false; // AWS gave us a bookmark, unlock it
        }

    }
    catch (error) {
        console.error(error);
        const listElement = document.getElementById('recipes-list');
        listElement.textContent = 'Unable to load recent recipes. Please check that the backend is running and try again.';
    }
}
function goForward() {
    if (nextBookmark) {
        currentPage++;
        keyHistory[currentPage] = nextBookmark; // Save the bookmark so we can go back later!
        loadRecipes(nextBookmark);
    }
}

function goBack() {
    if (currentPage > 0) {
        currentPage--;
        loadRecipes(keyHistory[currentPage]);
    }
}
window.onload = async() => {
    await handleLogin(); // First, check if they just logged in
    loadRecipes();       // Then, load the data
};