import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# API endpoints
IMBALANCE_URL = "https://api-baltic.transparency-dashboard.eu/api/v1/export"
ACTIVATION_URL = "https://api-baltic.transparency-dashboard.eu/api/v1/export"

# Create timezone objects
utc_tz = pytz.UTC
cet_tz = pytz.timezone('CET')

# Define time period in CET - exact start and end times
start_date_cet = cet_tz.localize(datetime.strptime("2024-09-23 00:00", "%Y-%m-%d %H:%M"))
end_date_cet = cet_tz.localize(datetime.strptime("2024-09-29 00:00", "%Y-%m-%d %H:%M"))

# Convert to UTC for API request - request slightly more data to ensure coverage
start_date_utc = (start_date_cet - timedelta(hours=3)).astimezone(utc_tz)  # Request extra time before
end_date_utc = (end_date_cet + timedelta(hours=3)).astimezone(utc_tz)     # Request extra time after

# Parameters for API requests with UTC times
imbalance_params = {
    'id': 'imbalance_volumes',
    'start_date': start_date_utc.strftime("%Y-%m-%dT%H:%M"),
    'end_date': end_date_utc.strftime("%Y-%m-%dT%H:%M"),
    'output_time_zone': 'CET',
    'output_format': 'json',
    'json_header_groups': '0'
}

activation_params = {
    'id': 'normal_activations_total',
    'start_date': start_date_utc.strftime("%Y-%m-%dT%H:%M"),
    'end_date': end_date_utc.strftime("%Y-%m-%dT%H:%M"),
    'output_time_zone': 'CET',
    'output_format': 'json',
    'json_header_groups': '0'
}

def fetch_data(url, params):
    """
    Fetch data from the Baltic Transparency Platform API
    """
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict) and 'data' in data:
            return data['data']
        return None
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return None

def process_data(data, data_type):
    """
    Process raw API data into structured DataFrame
    """
    try:
        timeseries = data.get('timeseries', [])
        df = pd.DataFrame(timeseries)
        
        # Convert timestamps to datetime with timezone info
        df['timestamp'] = pd.to_datetime(df['from']).dt.tz_convert('CET')
        df.set_index('timestamp', inplace=True)
        
        # Strict filtering to include only the exact requested time period
        df = df[(df.index >= start_date_cet) & (df.index < end_date_cet)]
        
        if data_type == "Imbalance":
            df['baltic_imbalance'] = df['values'].apply(lambda x: x[0])
        else:
            df['up_regulation'] = df['values'].apply(lambda x: x[0])
            df['down_regulation'] = df['values'].apply(lambda x: x[1])
        
        df = df.drop(['from', 'to', 'values'], axis=1)
        
        # Verify the data boundaries
        print(f"\n{data_type} DataFrame processed:")
        print(f"Start time: {df.index.min()}")
        print(f"End time: {df.index.max()}")
        print("\nFirst records:")
        print(df.head())
        print("\nLast records:")
        print(df.tail())
        
        return df
    except Exception as e:
        print(f"Error processing {data_type} data: {str(e)}")
        return pd.DataFrame()

def create_visualization(imbalance_df, activation_df):
    """
    Create visualization using metric units
    """
    try:
        # Set figure size in centimeters
        plt.figure(figsize=(38/2.54, 20/2.54))
        
        # Plot the data
        plt.plot(imbalance_df.index, imbalance_df['baltic_imbalance'], 
                label='Baltic Imbalance', color='blue', linewidth=1.5)
        plt.plot(activation_df.index, activation_df['up_regulation'], 
                label='Upward Regulation', color='green', linewidth=1.5)
        plt.plot(activation_df.index, -activation_df['down_regulation'], 
                label='Downward Regulation', color='red', linewidth=1.5)
        
        # Set x-axis limits to exact start and end times
        plt.xlim(start_date_cet, end_date_cet)
        
        # Format x-axis dates
        ax = plt.gca()
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
        
        # Add more x-axis ticks for better readability
        ax.xaxis.set_major_locator(plt.matplotlib.dates.DayLocator())
        
        # Add labels with metric units
        plt.title('Baltic Imbalance and Regulation Activities')
        plt.xlabel('Time (CET)')
        plt.ylabel('Power (MW)')
        
        # Customize appearance
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Add legend and adjust layout
        plt.legend()
        plt.tight_layout()
        
        # Save the visualization
        plt.savefig('baltic_regulation_analysis.png', dpi=300)
        print("\nVisualization saved as 'baltic_regulation_analysis.png'")
        
    except Exception as e:
        print(f"Error creating visualization: {str(e)}")

def analyze_regulation(imbalance_df, activation_df):
    """
    Analyze regulation effectiveness and patterns
    """
    try:
        # Merge the dataframes
        analysis_df = pd.merge(imbalance_df, activation_df, 
                             left_index=True, right_index=True, how='inner')
        
        # Calculate metrics
        analysis_df['imbalance_magnitude'] = abs(analysis_df['baltic_imbalance'])
        analysis_df['regulation_magnitude'] = (
            analysis_df['up_regulation'] + analysis_df['down_regulation']
        )
        
        # Calculate regulation effectiveness
        analysis_df['appropriate_regulation'] = (
            (analysis_df['baltic_imbalance'] > 0) & (analysis_df['down_regulation'] > 0) |
            (analysis_df['baltic_imbalance'] < 0) & (analysis_df['up_regulation'] > 0)
        )
        
        # Calculate temporal patterns
        analysis_df['hour'] = analysis_df.index.hour
        analysis_df['day'] = analysis_df.index.date
        
        # Calculate summary statistics
        total_periods = len(analysis_df)
        effective_periods = analysis_df['appropriate_regulation'].sum()
        effectiveness = (effective_periods / total_periods) * 100
        
        # Print analysis results
        print("\nRegulation Analysis:")
        print(f"Analysis period: {analysis_df.index.min()} to {analysis_df.index.max()}")
        print(f"Time period analyzed: {total_periods} hours")
        print(f"Effective regulation periods: {effective_periods} hours")
        print(f"Regulation effectiveness: {effectiveness:.2f}%")
        
        print("\nPower Metrics (MW):")
        print(f"Average imbalance magnitude: {analysis_df['imbalance_magnitude'].mean():.2f} MW")
        print(f"Maximum imbalance: {analysis_df['baltic_imbalance'].max():.2f} MW")
        print(f"Minimum imbalance: {analysis_df['baltic_imbalance'].min():.2f} MW")
        print(f"Average regulation magnitude: {analysis_df['regulation_magnitude'].mean():.2f} MW")
        
        # Calculate energy metrics
        print("\nEnergy Metrics (MWh):")
        total_imbalance_energy = analysis_df['imbalance_magnitude'].sum()
        total_regulation_energy = analysis_df['regulation_magnitude'].sum()
        print(f"Total imbalance energy: {total_imbalance_energy:.2f} MWh")
        print(f"Total regulation energy: {total_regulation_energy:.2f} MWh")
        
        # Save detailed analysis
        analysis_df.to_csv('regulation_analysis.csv')
        print("\nDetailed analysis saved to 'regulation_analysis.csv'")
        
        return analysis_df
        
    except Exception as e:
        print(f"Error in regulation analysis: {str(e)}")
        return pd.DataFrame()

def main():
    """Main execution function"""
    print("Analysis period (CET):")
    print(f"From: {start_date_cet.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"To: {end_date_cet.strftime('%Y-%m-%d %H:%M %Z')}")
    
    # Fetch data from APIs
    print("\nFetching imbalance data...")
    imbalance_data = fetch_data(IMBALANCE_URL, imbalance_params)
    
    print("\nFetching activation data...")
    activation_data = fetch_data(ACTIVATION_URL, activation_params)
    
    if imbalance_data and activation_data:
        # Process the raw data
        imbalance_df = process_data(imbalance_data, "Imbalance")
        activation_df = process_data(activation_data, "Activation")
        
        if not imbalance_df.empty and not activation_df.empty:
            # Create visualization and perform analysis
            create_visualization(imbalance_df, activation_df)
            analysis_df = analyze_regulation(imbalance_df, activation_df)
        else:
            print("No data available for processing")
    else:
        print("Failed to fetch data from one or both APIs")

if __name__ == "__main__":
    main()