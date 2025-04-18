<template>
  <div id="app">
    <div class="info-container">
      <h2>Find Climbing Crags</h2>

      <div>
        <label for="origin">Select your city of origin:</label>
        <select v-model="originCity" id="origin">
          <option disabled value=""></option>
          <option value="Montreal">Montreal</option>
          <option value="Quebec City">Quebec City</option>
          <option value="Ottawa">Ottawa</option>
          <option value="Toronto">Toronto</option>
          <option value="New York">New York</option>
        </select>
      </div>

      <label for="drive-time">How long are you looking to drive?</label>
      <select v-model="selectedTime" id="drive-time">
        <option value=""></option>
        <option value="1">1h (~100km)</option>
        <option value="2">2h (~200km)</option>
        <option value="3">3h (~300km)</option>
        <option value="4">4h (~400km)</option>
        <option value="5">5h (~500km)</option>
      </select>

      <div class="date-picker">
        <p>Please select up to 3 consecutive days in the next 7 days.</p>
        <label for="dateFrom">Date From:</label>
        <input type="date" v-model="dateFrom" id="dateFrom">
        <label for="dateTo">Date To:</label>
        <input type="date" v-model="dateTo" id="dateTo" :min="dateFrom">
      </div>

      <div v-if="isSingleDay">
        <label for="minTemp">Min Temperature (°C):</label>
        <input type="number" v-model.number="minTemp" id="minTemp">
        <label for="maxTemp">Max Temperature (°C):</label>
        <input type="number" v-model.number="maxTemp" id="maxTemp">
      </div>

      <div class="button-container">
        <button @click="fetchNearbyCrags">Search</button>
      </div>
    </div>

    <div class="results-container" v-if="nearbyCrags.length">
      <h2>Nearby Climbing Crags:</h2>
      <div class="sort-options">
        <label>Sort by:</label>
        <select v-model="sortOption" @change="sortCrags" :disabled="!isSingleDay">
          <option value="distance">Distance</option>
          <option value="temperature">Temperature</option>
        </select>
      </div>

      <ul>
        <li v-for="crag in nearbyCrags" :key="crag.name">
          <div style="display: flex; justify-content: space-between;"> 
            <input 
              type="checkbox" 
              :value="crag" 
              v-model="selectedCrags" 
              :disabled="selectedCrags.length >= 3 && !selectedCrags.includes(crag)"
              class="customCheckBox"
            />
            <strong style="text-align: left; width: 100%; align-content: center;">
              {{ crag.name }}
            </strong>
            <span style="white-space: nowrap;"> - {{ crag.distance }} km away</span>
          </div>
          <div style="display: flex; justify-content: flex-end;">{{ crag.climbs }} routes</div>
          <div v-if="crag.weather">
            <ul>
              <li v-for="(weather, date) in crag.weather" :key="date">
                <strong style="justify-content: flex-start; display: flex">{{ date }}</strong>
                <span v-if="weather.error">No forecast available</span>
                <span v-else>
                  <img :src="weather.icon" :alt="weather.description" width="50" height="50">
                  {{ weather.temperature }}°C - {{ weather.description }}
                </span>
              </li>
            </ul>
          </div>
        </li>
      </ul>

      <div class="email-input">
        <label for="email">Enter your email for updates:</label>
        <input type="email" v-model="userEmail" id="email" placeholder="your@email.com">
        <button @click="submitSelection" :disabled="selectedCrags.length === 0 || !userEmail">Save & Get Alerts</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      originCity: '',
      selectedTime: "",
      sortOption: "distance",
      nearbyCrags: [],
      dateFrom: "",
      dateTo: "",
      minTemp: null,
      maxTemp: null,
      userEmail: "",
      selectedCrags: []
    };
  },
  computed: {
    isSingleDay() {
      return this.dateFrom && this.dateTo && this.dateFrom === this.dateTo;
    }
  },
  methods: {
    async fetchNearbyCrags() {
      try {
        const response = await fetch("http://localhost:5000/find-crags", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            origin: this.originCity,
            hours: this.selectedTime,
            dateFrom: this.dateFrom,
            dateTo: this.dateTo,
            minTemp: this.minTemp,
            maxTemp: this.maxTemp
          })
        });

        const data = await response.json();

        // Ensure each crag has lat/lon
        this.nearbyCrags = data.map(crag => ({
          ...crag,
          lat: crag.lat,
          lon: crag.lon
        }));

        this.selectedCrags = [];
      } catch (error) {
        console.error("Error fetching crags:", error);
      }
    },
    sortCrags() {
      if (this.sortOption === "distance") {
        this.nearbyCrags.sort((a, b) => a.distance - b.distance);
      } else if (this.sortOption === "temperature" && this.isSingleDay) {
        this.nearbyCrags.sort((a, b) => {
          const tempA = a.weather?.[this.dateFrom]?.temperature || 0;
          const tempB = b.weather?.[this.dateFrom]?.temperature || 0;
          return tempB - tempA;
        });
      }
    },
    async submitSelection() {
      try {
        const response = await fetch("http://localhost:5000/subscribe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: this.userEmail,
            dateFrom: this.dateFrom,
            dateTo: this.dateTo,
            selectedCrags: this.selectedCrags
          })
        });

        const result = await response.json();
        alert(result.message || "Subscription complete!");
      } catch (error) {
        console.error("Subscription error:", error);
      }
    }
  }
};
</script>

<style scoped>
/* Add your styles here */
</style>




<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

body {
  font-family: 'Poppins', sans-serif;
}

#app {
  min-height: 100vh;
  background: url('@/assets/imgur.jpg') no-repeat center center fixed;
  background-size: cover;
  color: white;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* 🎯 New Frame Container for Info */
.info-container {
  background: rgba(0, 0, 0, 0.6);
  padding: 20px;
  border-radius: 10px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  
}

.results-container {
  background: rgba(0, 0, 0, 0.6);
  padding: 20px;
  border-radius: 10px;
  width: 90%;
  max-width: 600px;
  margin-top: 20px;
}

h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 15px;
}

p {
  font-size: 18px;
  line-height: 1.6;
}

label {
  font-weight: 400;
  font-size: 16px;
  display: block;
  margin-top: 10px;
}

select, input {
  width: 100%;
  padding: 10px;
  margin-top: 5px;
  border-radius: 5px;
  border: none;
  text-align: center;
}
.customCheckBox {
  width: auto;
}

/* ✨ Styled Buttons */
button {
  background: #ff6600;
  color: white;
  border: none;
  padding: 12px 15px;
  margin-top: 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.3s ease;
}

button:hover {
  background: #e65c00;
}

/* 📋 Styling for Results */
ul {
  list-style: none;
  padding: 0;
  
}

li {
  background: rgba(0, 0, 0, 0.5);
  padding: 10px;
  margin: 5px;
  border-radius: 5px;
  
}

/* 🌟 Improved Date Picker Alignment */
.date-picker {
  margin-top: 10px;
  margin-right: 20px;
}

</style>

