#!/usr/bin/env python3
"""Simple script to diagnose why no recommendations are available."""

import requests
import json

def check_recommendations():
    """Check the recommendations system status."""
    
    print("🔍 Diagnosing Recommendations System")
    print("=" * 50)
    
    base_url = "http://localhost/api/v1"
    
    try:
        # 1. Check current recommendations
        print("\n1. Checking current recommendations...")
        response = requests.get(f"{base_url}/recommendations/current", timeout=5)
        if response.status_code == 200:
            recommendations = response.json()
            print(f"   ✅ API accessible, {len(recommendations)} recommendations found")
            if recommendations:
                print("   📊 Sample recommendation:")
                for rec in recommendations[:1]:
                    print(f"      Symbol: {rec.get('symbol', 'N/A')}")
                    print(f"      Score: {rec.get('score', 'N/A')}")
                    print(f"      Created: {rec.get('created_at', 'N/A')}")
            else:
                print("   ❌ No recommendations found")
        else:
            print(f"   ❌ API error: {response.status_code}")
            return
            
        # 2. Check debug endpoint
        print("\n2. Checking system status...")
        try:
            response = requests.get(f"{base_url}/recommendations/debug", timeout=10)
            if response.status_code == 200:
                debug_info = response.json()
                print(f"   ✅ Debug endpoint accessible")
                print(f"   📊 Active tickers: {debug_info.get('active_tickers', 'N/A')}")
                print(f"   📊 Total quotes: {debug_info.get('total_quotes', 'N/A')}")
                print(f"   📊 Total options: {debug_info.get('total_options', 'N/A')}")
                print(f"   📊 Recent options: {debug_info.get('recent_options', 'N/A')}")
                print(f"   📊 Total recommendations: {debug_info.get('total_recommendations', 'N/A')}")
                print(f"   📊 Today's recommendations: {debug_info.get('todays_recommendations', 'N/A')}")
                
                if debug_info.get('most_recent_recommendation'):
                    recent = debug_info['most_recent_recommendation']
                    print(f"   📊 Most recent: {recent.get('symbol')} at {recent.get('created_at')}")
                
                # Analyze the problem
                print(f"\n🔍 Problem Analysis:")
                if debug_info.get('active_tickers', 0) == 0:
                    print("   ❌ ISSUE: No active tickers in database")
                    print("   💡 SOLUTION: Run S&P 500 universe update")
                elif debug_info.get('total_quotes', 0) == 0:
                    print("   ❌ ISSUE: No ticker quotes available")
                    print("   💡 SOLUTION: Refresh market data")
                elif debug_info.get('total_options', 0) == 0:
                    print("   ❌ ISSUE: No options data available")
                    print("   💡 SOLUTION: Fetch options data")
                elif debug_info.get('recent_options', 0) == 0:
                    print("   ❌ ISSUE: No recent options data (>24h old)")
                    print("   💡 SOLUTION: Refresh options data")
                elif debug_info.get('todays_recommendations', 0) == 0:
                    print("   ⚠️  ISSUE: No recommendations generated today")
                    print("   💡 SOLUTION: Generate new recommendations")
                else:
                    print("   ✅ Data appears to be available - check recommendation generation logic")
                    
            else:
                print(f"   ❌ Debug endpoint error: {response.status_code}")
        except requests.RequestException as e:
            print(f"   ❌ Debug endpoint failed: {e}")
        
        # 3. Try generating new recommendations
        print(f"\n3. Checking recommendation generation...")
        print("   ⚠️  Generation can take 30+ seconds, skipping for now")
        print("   💡 To manually generate: curl -X POST http://localhost/api/v1/recommendations/refresh")
        
    except requests.RequestException as e:
        print(f"❌ Failed to connect to API: {e}")
        print("💡 Make sure the backend is running: just dev-status")

if __name__ == "__main__":
    check_recommendations()
