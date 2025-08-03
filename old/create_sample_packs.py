#!/usr/bin/env python3
"""
Script to create sample prompt packs for the application
"""

import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PromptPack

def create_sample_packs():
    """Create sample prompt packs"""
    
    app = create_app()
    
    with app.app_context():
        # Check if packs already exist
        existing_packs = PromptPack.query.count()
        if existing_packs > 0:
            print(f"Found {existing_packs} existing prompt packs. Skipping creation.")
            return
        
        # Sample prompt packs
        packs = [
            {
                "name": "Nature & Wildlife",
                "description": "Breathtaking scenes from the natural world, featuring wildlife, landscapes, and environmental beauty.",
                "category": "nature",
                "featured": True,
                "prompts": [
                    {
                        "text": "A majestic eagle soaring over snow-capped mountains at golden hour, cinematic lighting, 8K quality",
                        "description": "Epic wildlife scene with dramatic lighting"
                    },
                    {
                        "text": "Timelapse of a blooming flower garden with butterflies dancing in the sunlight, macro photography style",
                        "description": "Peaceful nature timelapse"
                    },
                    {
                        "text": "A serene lake reflecting the sunset with a family of ducks swimming peacefully, warm golden tones",
                        "description": "Tranquil water scene"
                    },
                    {
                        "text": "A dense rainforest with sunlight filtering through the canopy, misty atmosphere, tropical birds flying",
                        "description": "Lush rainforest environment"
                    },
                    {
                        "text": "A lone wolf standing on a rocky cliff overlooking a vast valley, dramatic storm clouds gathering",
                        "description": "Wild and dramatic landscape"
                    }
                ]
            },
            {
                "name": "Sci-Fi & Futuristic",
                "description": "Futuristic cityscapes, space exploration, and advanced technology scenes.",
                "category": "sci-fi",
                "featured": True,
                "prompts": [
                    {
                        "text": "A futuristic city with flying cars, neon lights, and towering skyscrapers, cyberpunk aesthetic",
                        "description": "Cyberpunk cityscape"
                    },
                    {
                        "text": "A spaceship traveling through a colorful nebula with stars and planets in the background",
                        "description": "Space exploration scene"
                    },
                    {
                        "text": "A robot walking through a high-tech laboratory with holographic displays and advanced machinery",
                        "description": "Futuristic laboratory"
                    },
                    {
                        "text": "A time portal opening in a modern city street, with people and objects being pulled into it",
                        "description": "Sci-fi time travel"
                    },
                    {
                        "text": "A space station orbiting Earth with astronauts floating in zero gravity, Earth's blue glow",
                        "description": "Space station scene"
                    }
                ]
            },
            {
                "name": "Business & Professional",
                "description": "Professional business environments, corporate settings, and workplace scenarios.",
                "category": "business",
                "featured": True,
                "prompts": [
                    {
                        "text": "A modern office with people collaborating around a glass conference table, natural lighting",
                        "description": "Professional meeting scene"
                    },
                    {
                        "text": "A business presentation with charts and graphs on a large screen, audience listening attentively",
                        "description": "Business presentation"
                    },
                    {
                        "text": "A startup team brainstorming in a creative workspace with whiteboards and colorful sticky notes",
                        "description": "Creative collaboration"
                    },
                    {
                        "text": "A handshake between business partners in a sleek corporate lobby, professional attire",
                        "description": "Business partnership"
                    },
                    {
                        "text": "A laptop on a desk with coffee cup, showing graphs and data, warm office lighting",
                        "description": "Work from home setup"
                    }
                ]
            },
            {
                "name": "Art & Creative",
                "description": "Artistic scenes, creative processes, and visually stunning compositions.",
                "category": "art",
                "featured": False,
                "prompts": [
                    {
                        "text": "An artist's paintbrush creating colorful strokes on a canvas, paint splattering in slow motion",
                        "description": "Artistic creation process"
                    },
                    {
                        "text": "A digital art studio with multiple screens showing different creative projects, vibrant colors",
                        "description": "Digital art workspace"
                    },
                    {
                        "text": "A sculptor working with clay, hands shaping a beautiful figure, studio lighting",
                        "description": "Sculpture creation"
                    },
                    {
                        "text": "A photographer taking pictures in a studio with professional lighting and equipment",
                        "description": "Photography studio"
                    },
                    {
                        "text": "A street artist painting a mural on a city wall, people watching and appreciating",
                        "description": "Street art creation"
                    }
                ]
            },
            {
                "name": "Travel & Adventure",
                "description": "Exotic locations, travel experiences, and adventure activities around the world.",
                "category": "travel",
                "featured": False,
                "prompts": [
                    {
                        "text": "A backpacker hiking through a beautiful mountain trail with stunning valley views",
                        "description": "Mountain hiking adventure"
                    },
                    {
                        "text": "A beach sunset with palm trees swaying, crystal clear water, tropical paradise",
                        "description": "Tropical beach scene"
                    },
                    {
                        "text": "A hot air balloon floating over a colorful landscape, sunrise lighting",
                        "description": "Hot air balloon adventure"
                    },
                    {
                        "text": "A street market in a foreign city with colorful stalls and people shopping",
                        "description": "Cultural market scene"
                    },
                    {
                        "text": "A camper van parked by a lake with mountains in the background, peaceful camping scene",
                        "description": "Camping adventure"
                    }
                ]
            },
            {
                "name": "Food & Culinary",
                "description": "Delicious food preparation, cooking scenes, and culinary experiences.",
                "category": "food",
                "featured": False,
                "prompts": [
                    {
                        "text": "A chef cooking in a professional kitchen with flames and steam, culinary artistry",
                        "description": "Professional cooking scene"
                    },
                    {
                        "text": "Fresh ingredients being chopped and prepared on a wooden cutting board, close-up shots",
                        "description": "Food preparation"
                    },
                    {
                        "text": "A beautiful cake being decorated with frosting and sprinkles, birthday celebration",
                        "description": "Cake decoration"
                    },
                    {
                        "text": "A family enjoying a home-cooked meal around a dining table, warm lighting",
                        "description": "Family dinner scene"
                    },
                    {
                        "text": "A coffee barista making latte art, steam rising from the cup, cozy cafe atmosphere",
                        "description": "Coffee making process"
                    }
                ]
            }
        ]
        
        # Create the prompt packs
        for pack_data in packs:
            pack = PromptPack(
                name=pack_data["name"],
                description=pack_data["description"],
                category=pack_data["category"],
                featured=pack_data["featured"],
                prompts=pack_data["prompts"]
            )
            db.session.add(pack)
        
        # Commit to database
        db.session.commit()
        print(f"Created {len(packs)} sample prompt packs!")
        
        # Print summary
        for pack in PromptPack.query.all():
            print(f"- {pack.name} ({pack.category}): {len(pack.prompts) if pack.prompts else 0} prompts")

if __name__ == "__main__":
    create_sample_packs() 