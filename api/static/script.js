const API_URL = '/api/historical/NIFTY50'; // Default, overridden by HTML
const LOW_NEARNESS_THRESHOLD = 20;

async function fetchData() {
    // 1. Define variables at the start of the function
    const cardGridContainer = document.getElementById('stock-card-grid');
    const statusMessage = document.getElementById('status-message');

    // Safety check for UI elements
    if (!cardGridContainer || !statusMessage) {
        console.error("Critical HTML elements (card-grid or status-message) are missing.");
        return;
    }

    // Display initial loading message (using div structure)
    cardGridContainer.innerHTML = '<div style="text-align: center; padding: 20px;">Fetching live data...</div>';
    statusMessage.textContent = 'Fetching live data...';


    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const apiData = await response.json();

        // Clear the loading message
        cardGridContainer.innerHTML = '';

        // 1. Update status message
        const indexName = apiData.index || 'Stocks';
        const total = apiData.total_constituents || apiData.data.length;

        statusMessage.textContent = `Displaying data for ${total} ${indexName} stocks. (Near-Low Threshold: ${LOW_NEARNESS_THRESHOLD}% of range)`;

        // 2. Iterate and build the card elements
        apiData.data.forEach(stock => {
            // Determine the highlight class based on nearness
            const nearness = stock.lowNearnessPercentage;
            let highlightClass = '';
            if (nearness !== null && nearness <= LOW_NEARNESS_THRESHOLD) {
                highlightClass = 'near-low-highlight';
            }

            // Format fields
            const lastPrice = stock.lastPrice ? `₹ ${stock.lastPrice.toLocaleString('en-IN')}` : 'N/A';
            const high52W = stock.high52Week ? `₹ ${stock.high52Week.toLocaleString('en-IN')}` : 'N/A';
            const low52W = stock.low52Week ? `₹ ${stock.low52Week.toLocaleString('en-IN')}` : 'N/A';
            const events = stock.upcomingEvents.map(e => `${e.type} on ${e.date}`).join(', ') || 'None';
            const nearnessText = nearness !== null ? `${nearness}%` : 'N/A';

            // Construct the HTML for a single, beautiful card
            const cardHTML = `
                <div class="stock-card ${highlightClass}">
                    <div class="card-header">
                        <a href="${stock.detailLink}" target="_blank" class="symbol-link">${stock.symbol}</a>
                        <span class="company-name">${stock.name}</span>
                    </div>
                    
                    <div class="price-section">
                        <div class="price-label">Last Price</div>
                        <div class="price-value">${lastPrice}</div>
                    </div>

                    <div class="metric-group">
                        <div class="metric">
                            <span class="metric-label">52W High:</span>
                            <span class="metric-value">${high52W}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">52W Low:</span>
                            <span class="metric-value">${low52W}</span>
                        </div>
                        <div class="metric near-low">
                            <span class="metric-label">Near Low:</span>
                            <span class="metric-value">${nearnessText}</span>
                        </div>
                    </div>

                    <div class="event-section">
                        <span class="event-label">Events:</span>
                        <span class="event-value">${events}</span>
                    </div>
                </div>
            `;

            cardGridContainer.insertAdjacentHTML('beforeend', cardHTML); // Insert into the correct container
        });

    } catch (error) {
        cardGridContainer.innerHTML = `<div style="text-align: center; padding: 20px; color: red;">🛑 Error fetching data: ${error.message}. Check Flask console.</div>`;
        statusMessage.textContent = "🛑 Data Error.";
        console.error("Error:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('stock-card-grid')) {
        fetchData();
    }
});