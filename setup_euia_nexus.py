"""
Setup EU IA Nexus: Create EU IA structure and map to Belgian 21 themes

This script creates:
1. EU IA Category nodes (Economic, Social, Environmental)
2. EU IA Subcategory nodes with key questions
3. Mappings from Belgian 21 themes to EU IA subcategories
"""

import os
from neo4j import GraphDatabase
from typing import Dict, List, Any

# Load environment variables from .env files
try:
    from dotenv import load_dotenv
    # Try .env.neo4j first (if it exists), then .env
    load_dotenv('.env.neo4j')  # Load Neo4j-specific credentials
    load_dotenv()  # Load general .env file (will not override existing vars)
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Continuing with system environment variables...")
except Exception as e:
    print(f"⚠️  Could not load .env files: {e}")
    print("   Continuing with system environment variables...")

# EU IA Structure from Tool #19
EU_IA_CATEGORIES = {
    "economic": {
        "name": "Economic",
        "subcategories": {
            "operating_costs": {
                "name": "Operating costs and conduct of business",
                "key_questions": [
                    "Will it impose additional adjustment, compliance or transaction costs on businesses?",
                    "How does the option affect the cost or availability of essential inputs?",
                    "Does it affect access to finance?",
                    "Does it impact on the investment cycle?",
                    "Will it entail the withdrawal of certain products from the market?",
                    "Will it entail stricter regulation of the conduct of a particular business?",
                ]
            },
            "administrative_burdens": {
                "name": "Administrative burdens on businesses",
                "key_questions": [
                    "Does it affect the nature of information obligations placed on businesses?",
                    "What is the type of data required, reporting frequency, complexity of submission process?",
                ]
            },
            "trade_investment": {
                "name": "Trade and investment flows",
                "key_questions": [
                    "How will the option affect exports and imports out of and into the EU?",
                    "How will investment flows be affected and the trade in services?",
                    "Will the option give rise to trade, customs or other non-trade barriers?",
                ]
            },
            "competitiveness": {
                "name": "Competitiveness (sectoral) of business",
                "key_questions": [
                    "What impact does the option have on the cost of doing business?",
                    "What impact does the option have on a business' capacity to innovate?",
                    "What impact does the policy option have on a business' market share?",
                ]
            },
            "smes": {
                "name": "Position of SMEs",
                "key_questions": [
                    "What is the impact of identified additional costs and burdens on the operation and competitiveness of SMEs?",
                ]
            },
            "innovation_research": {
                "name": "Innovation and research",
                "key_questions": [
                    "Does the option stimulate or hinder research and development?",
                    "Does it facilitate the introduction and dissemination of new production methods?",
                    "Does it affect the protection and enforcement of intellectual property rights?",
                ]
            },
            "public_authorities": {
                "name": "Public authorities",
                "key_questions": [
                    "Does the option have budgetary consequences for public authorities at different levels?",
                ]
            },
            "macroeconomic": {
                "name": "Macroeconomic environment",
                "key_questions": [
                    "Does it have overall consequences for economic growth and employment?",
                    "How does the option contribute to improving the conditions for investment?",
                ]
            },
        }
    },
    "social": {
        "name": "Social",
        "subcategories": {
            "employment": {
                "name": "Employment",
                "key_questions": [
                    "To what extent are new jobs created or lost?",
                    "Are direct jobs created or lost in specific sectors, professions, regions?",
                    "Are there significant indirect effects which might change employment levels?",
                ]
            },
            "working_conditions": {
                "name": "Working Conditions",
                "key_questions": [
                    "Does the option affect wages, labour costs or wage setting mechanisms?",
                    "Does the option affect employment protection?",
                    "Does the option affect occupational health and safety?",
                ]
            },
            "income_distribution": {
                "name": "Income distribution, social protection and social inclusion",
                "key_questions": [
                    "Does the option affect peoples'/households' income and at risk of poverty rates?",
                    "Does the option affect inequalities and the distribution of incomes and wealth?",
                    "Does the option affect the access to and quality of social protection benefits?",
                ]
            },
            "public_health": {
                "name": "Public health and safety and health systems",
                "key_questions": [
                    "Does the option affect the health and safety of individuals/populations?",
                    "Does the option increase or decrease the likelihood of health risks?",
                    "Does the option affect the quality and/or access to health services?",
                ]
            },
            "education": {
                "name": "Education and training, and education and training systems",
                "key_questions": [
                    "Does the option affect the level of education and training outcomes?",
                    "Does the option affect the access of individuals to education or training?",
                    "Does the option affect the financing and organisation of education systems?",
                ]
            },
            "crime_security": {
                "name": "Crime, Terrorism and Security",
                "key_questions": [
                    "Does the option improve or hinder security, or impact on crime or terrorism risks?",
                    "Does the option affect the criminal's chances of detection?",
                    "Does it affect law enforcement capacity to address criminal activity?",
                ]
            },
            "culture": {
                "name": "Culture",
                "key_questions": [
                    "Does the proposal have an impact on the preservation of cultural heritage?",
                    "Does the proposal have an impact on cultural diversity?",
                ]
            },
        }
    },
    "environmental": {
        "name": "Environmental",
        "subcategories": {
            "climate": {
                "name": "Climate",
                "key_questions": [
                    "Does the option affect the emission of greenhouse gases?",
                    "Does the option affect economic incentives set up by market based mechanisms (MBMs)?",
                    "Does the option affect the emission of ozone depleting substances?",
                    "Does the option affect our ability to adapt to climate change?",
                ]
            },
            "air_quality": {
                "name": "Air quality",
                "key_questions": [
                    "Does the option have an effect on emissions of acidifying, eutrophying, photochemical or harmful air pollutants?",
                ]
            },
            "water": {
                "name": "Water quality and resources",
                "key_questions": [
                    "Does the option decrease or increase the quality or quantity of freshwater and groundwater?",
                    "Does it raise or lower the quality of waters in coastal and marine areas?",
                    "Does it affect drinking water resources?",
                ]
            },
            "biodiversity": {
                "name": "Biodiversity, flora, fauna and landscapes",
                "key_questions": [
                    "Does the option reduce the number of species/varieties/races in any area?",
                    "Does it affect protected or endangered species or their habitats?",
                    "Does it split the landscape into smaller areas or affect migration routes?",
                ]
            },
            "soil": {
                "name": "Soil quality or resources",
                "key_questions": [
                    "Does the option affect the acidification, contamination or salinity of soil?",
                    "Does it lead to loss of available soil or increase the amount of usable soil?",
                ]
            },
            "waste": {
                "name": "Waste production, generation and recycling",
                "key_questions": [
                    "Does the option affect waste production or how waste is treated, disposed of or recycled?",
                ]
            },
            "resources": {
                "name": "Efficient use of resources (renewable & non-renewable)",
                "key_questions": [
                    "Does the option affect the use of renewable resources?",
                    "Does it reduce or increase use of non-renewable resources?",
                ]
            },
            "sustainable_consumption": {
                "name": "Sustainable consumption and production",
                "key_questions": [
                    "Does the option lead to more sustainable production and consumption?",
                    "Does the option change the relative prices of environmental friendly and unfriendly products?",
                ]
            },
            "transport_energy": {
                "name": "Transport and the use of energy",
                "key_questions": [
                    "Does the option affect the energy intensity of the economy?",
                    "Does the option affect the fuel mix used in energy production?",
                    "Will it increase or decrease the demand for transport?",
                    "Does it increase or decrease vehicle emissions?",
                ]
            },
            "animal_welfare": {
                "name": "Animal welfare",
                "key_questions": [
                    "Does the option have an impact on health of animals?",
                    "Does the option affect animal welfare (i.e. humane treatment of animals)?",
                ]
            },
            "environmental_risks": {
                "name": "The likelihood or scale of environmental risks",
                "key_questions": [
                    "Does the option affect the likelihood or prevention of fire, explosions, breakdowns, accidents?",
                    "Does it affect the risk of unauthorised or unintentional dissemination of environmentally alien or genetically modified organisms?",
                ]
            },
            "land_use": {
                "name": "Land use",
                "key_questions": [
                    "Does the option have the effect of bringing new areas of land into use for the first time?",
                    "Does it affect land designated as sensitive for ecological reasons?",
                ]
            },
        }
    }
}

# Mapping: Belgian 21 Themes → EU IA Subcategories
BELGIAN_THEME_MAPPINGS = {
    1: {  # Fight against poverty
        "name": "Fight against poverty",
        "euia_mappings": [
            ("social", "income_distribution", "primary", 0.95),
        ]
    },
    2: {  # Equal opportunities and social cohesion
        "name": "Equal opportunities and social cohesion",
        "euia_mappings": [
            ("social", "income_distribution", "primary", 0.90),
        ]
    },
    3: {  # Equality between women and men
        "name": "Equality between women and men",
        "euia_mappings": [
            ("social", "income_distribution", "primary", 0.85),
            ("social", "working_conditions", "secondary", 0.75),
        ]
    },
    4: {  # Health
        "name": "Health",
        "euia_mappings": [
            ("social", "public_health", "primary", 0.98),
        ]
    },
    5: {  # Employment
        "name": "Employment",
        "euia_mappings": [
            ("social", "employment", "primary", 0.98),
            ("social", "working_conditions", "primary", 0.90),
        ]
    },
    6: {  # Consumption and production patterns
        "name": "Consumption and production patterns",
        "euia_mappings": [
            ("environmental", "sustainable_consumption", "primary", 0.95),
            ("environmental", "resources", "secondary", 0.80),
        ]
    },
    7: {  # Economic development
        "name": "Economic development",
        "euia_mappings": [
            ("economic", "macroeconomic", "primary", 0.90),
            ("economic", "competitiveness", "primary", 0.85),
            ("economic", "trade_investment", "secondary", 0.75),
        ]
    },
    8: {  # Investments
        "name": "Investments",
        "euia_mappings": [
            ("economic", "macroeconomic", "primary", 0.90),
            ("economic", "innovation_research", "secondary", 0.80),
        ]
    },
    9: {  # Research and development
        "name": "Research and development",
        "euia_mappings": [
            ("economic", "innovation_research", "primary", 0.98),
        ]
    },
    10: {  # SMEs
        "name": "SMEs (Small and Medium-Sized Enterprises)",
        "euia_mappings": [
            ("economic", "smes", "primary", 0.98),
            ("economic", "operating_costs", "primary", 0.90),
        ]
    },
    11: {  # Administrative burdens
        "name": "Administrative burdens",
        "euia_mappings": [
            ("economic", "administrative_burdens", "primary", 0.98),
        ]
    },
    12: {  # Energy
        "name": "Energy",
        "euia_mappings": [
            ("environmental", "transport_energy", "primary", 0.95),
            ("environmental", "resources", "primary", 0.90),
            ("environmental", "climate", "secondary", 0.85),
        ]
    },
    13: {  # Mobility
        "name": "Mobility",
        "euia_mappings": [
            ("environmental", "transport_energy", "primary", 0.95),
            ("environmental", "air_quality", "secondary", 0.80),
        ]
    },
    14: {  # Food
        "name": "Food",
        "euia_mappings": [
            ("environmental", "sustainable_consumption", "primary", 0.85),
            ("environmental", "animal_welfare", "secondary", 0.75),
        ]
    },
    15: {  # Climate change
        "name": "Climate change",
        "euia_mappings": [
            ("environmental", "climate", "primary", 0.98),
        ]
    },
    16: {  # Natural resources
        "name": "Natural resources",
        "euia_mappings": [
            ("environmental", "water", "primary", 0.90),
            ("environmental", "soil", "primary", 0.85),
            ("environmental", "resources", "primary", 0.90),
            ("environmental", "biodiversity", "secondary", 0.75),
        ]
    },
    17: {  # Indoor and outdoor air
        "name": "Indoor and outdoor air",
        "euia_mappings": [
            ("environmental", "air_quality", "primary", 0.98),
        ]
    },
    18: {  # Biodiversity
        "name": "Biodiversity",
        "euia_mappings": [
            ("environmental", "biodiversity", "primary", 0.98),
        ]
    },
    19: {  # Nuisances
        "name": "Nuisances",
        "euia_mappings": [
            ("environmental", "environmental_risks", "primary", 0.85),
            ("environmental", "air_quality", "secondary", 0.70),
        ]
    },
    20: {  # Public authorities
        "name": "Public authorities",
        "euia_mappings": [
            ("economic", "public_authorities", "primary", 0.95),
        ]
    },
    21: {  # Policy coherence for development
        "name": "Policy coherence for development",
        "euia_mappings": [
            ("economic", "trade_investment", "primary", 0.85),
            ("social", "income_distribution", "secondary", 0.70),
        ]
    },
}


def get_neo4j_connection():
    """Get Neo4j connection from environment variables."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    if not uri:
        instance_id = os.getenv("AURA_INSTANCEID")
        if instance_id:
            uri = f"neo4j+s://{instance_id}.databases.neo4j.io"
    
    if not uri or not password:
        raise ValueError(
            "Neo4j connection details required. Set NEO4J_URI/NEO4J_PASSWORD or AURA_INSTANCEID"
        )
    
    return GraphDatabase.driver(uri, auth=(username, password))


def create_euia_structure(driver):
    """Create EU IA category and subcategory nodes."""
    print("\n📊 Creating EU IA structure...")
    
    with driver.session() as session:
        # Create categories
        for category_id, category_data in EU_IA_CATEGORIES.items():
            print(f"  Creating category: {category_data['name']}")
            
            # Create category node
            session.run("""
                MERGE (cat:EUIACategory {id: $id})
                SET cat.category_name = $name,
                    cat.source = "EU Impact Assessment Guidelines",
                    cat.tool_number = 19
            """, id=f"euia:{category_id}", name=category_data["name"])
            
            # Create subcategories
            for subcat_id, subcat_data in category_data["subcategories"].items():
                print(f"    Creating subcategory: {subcat_data['name']}")
                
                subcat_node_id = f"euia:{category_id}:{subcat_id}"
                
                # Create subcategory node
                session.run("""
                    MERGE (sub:EUIASubcategory {id: $id})
                    SET sub.subcategory_name = $name,
                        sub.parent_category = $parent,
                        sub.key_questions = $questions,
                        sub.source = "Tool #19"
                """, 
                    id=subcat_node_id,
                    name=subcat_data["name"],
                    parent=category_id,
                    questions=subcat_data["key_questions"]
                )
                
                # Link subcategory to category
                session.run("""
                    MATCH (cat:EUIACategory {id: $cat_id})
                    MATCH (sub:EUIASubcategory {id: $sub_id})
                    MERGE (cat)-[:HAS_SUBCATEGORY]->(sub)
                """, 
                    cat_id=f"euia:{category_id}",
                    sub_id=subcat_node_id
                )
        
        print("✅ EU IA structure created")


def create_belgian_themes(driver):
    """Create Belgian 21 theme nodes if they don't exist."""
    print("\n📋 Creating Belgian theme nodes...")
    
    with driver.session() as session:
        for theme_num, theme_data in BELGIAN_THEME_MAPPINGS.items():
            session.run("""
                MERGE (t:Theme {theme_number: $num})
                SET t.name = $name,
                    t.id = $id,
                    t.belgian_ria = true
            """, 
                num=theme_num,
                name=theme_data["name"],
                id=f"theme:{theme_num}"
            )
        
        print("✅ Belgian theme nodes created/verified")


def create_mappings(driver):
    """Create mappings between Belgian themes and EU IA subcategories."""
    print("\n🔗 Creating theme → EU IA mappings...")
    
    with driver.session() as session:
        for theme_num, theme_data in BELGIAN_THEME_MAPPINGS.items():
            theme_name = theme_data["name"]
            print(f"  Mapping theme #{theme_num}: {theme_name}")
            
            for category_id, subcat_id, mapping_strength, relevance_score in theme_data["euia_mappings"]:
                subcat_node_id = f"euia:{category_id}:{subcat_id}"
                cat_node_id = f"euia:{category_id}"
                
                # Map theme to subcategory
                session.run("""
                    MATCH (t:Theme {theme_number: $theme_num})
                    MATCH (sub:EUIASubcategory {id: $sub_id})
                    MERGE (t)-[r:MAPPED_TO]->(sub)
                    SET r.mapping_strength = $strength,
                        r.relevance_score = $score,
                        r.mapped_at = datetime()
                """,
                    theme_num=theme_num,
                    sub_id=subcat_node_id,
                    strength=mapping_strength,
                    score=relevance_score
                )
                
                # Map theme to category (if primary mapping)
                if mapping_strength == "primary":
                    session.run("""
                        MATCH (t:Theme {theme_number: $theme_num})
                        MATCH (cat:EUIACategory {id: $cat_id})
                        MERGE (t)-[r:MAPPED_TO_CATEGORY]->(cat)
                        SET r.primary_category = true,
                            r.coverage_percentage = $score
                    """,
                        theme_num=theme_num,
                        cat_id=cat_node_id,
                        score=relevance_score
                    )
        
        print("✅ Mappings created")


def verify_structure(driver):
    """Verify the created structure."""
    print("\n🔍 Verifying structure...")
    
    with driver.session() as session:
        # Count nodes
        result = session.run("MATCH (n:EUIACategory) RETURN count(n) as count")
        cat_count = result.single()["count"]
        print(f"  EU IA Categories: {cat_count}")
        
        result = session.run("MATCH (n:EUIASubcategory) RETURN count(n) as count")
        subcat_count = result.single()["count"]
        print(f"  EU IA Subcategories: {subcat_count}")
        
        result = session.run("MATCH (n:Theme) WHERE n.belgian_ria = true RETURN count(n) as count")
        theme_count = result.single()["count"]
        print(f"  Belgian Themes: {theme_count}")
        
        result = session.run("MATCH ()-[r:MAPPED_TO]->() RETURN count(r) as count")
        mapping_count = result.single()["count"]
        print(f"  Theme → Subcategory Mappings: {mapping_count}")
        
        # Example query: Get key questions for a theme
        result = session.run("""
            MATCH (t:Theme {theme_number: 15})-[r:MAPPED_TO]->(sub:EUIASubcategory)
            WHERE r.mapping_strength = "primary"
            RETURN t.name, sub.subcategory_name, sub.key_questions
            LIMIT 1
        """)
        record = result.single()
        if record:
            print(f"\n  Example: Theme '{record['t.name']}' → '{record['sub.subcategory_name']}'")
            print(f"    Key Questions: {len(record['sub.key_questions'])} questions")
    
    print("✅ Verification complete")


def main():
    """Main execution."""
    print("=" * 70)
    print("EU IA NEXUS SETUP")
    print("=" * 70)
    
    try:
        driver = get_neo4j_connection()
        
        # Step 1: Create EU IA structure
        create_euia_structure(driver)
        
        # Step 2: Create Belgian themes
        create_belgian_themes(driver)
        
        # Step 3: Create mappings
        create_mappings(driver)
        
        # Step 4: Verify
        verify_structure(driver)
        
        print("\n" + "=" * 70)
        print("✅ SETUP COMPLETE!")
        print("=" * 70)
        print("\nYou can now query the nexus using Cypher queries.")
        print("Example: MATCH (t:Theme {theme_number: 15})-[r:MAPPED_TO]->(sub:EUIASubcategory)")
        print("         RETURN t.name, sub.subcategory_name, sub.key_questions")
        
        driver.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
