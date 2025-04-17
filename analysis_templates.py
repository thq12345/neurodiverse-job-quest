"""
Pre-computed work environment analyses for all possible answer combinations.
This file contains the analyses for all 36 possible combinations of answers
to the first 4 multiple choice questions.
"""

# Map each answer combination to a pre-computed analysis
# Key format: "Q1Q2Q3Q4" where each Q is the option letter (A, B, C)
# analysis_templates = {
#     # Q1=A (structured schedule), Q2=A (quiet spaces), Q3=A (minimal interactions), Q4=A (detailed and focused)
#     "AAAA": {
#         "work_style": {
#             "description": "Highly structured and independent work environment",
#             "explanation": "You thrive with a structured schedule and prefer focusing on detailed work without interruptions."
#         },
#         "environment": {
#             "description": "Quiet, private workspace with minimal distractions",
#             "explanation": "Your preference for quiet spaces and minimal interactions indicates you work best in a low-distraction environment."
#         },
#         "interaction_level": {
#             "description": "Minimal social interaction with clearly defined communication channels",
#             "explanation": "You've indicated a preference for limited interactions, suggesting you work best independently with focused time."
#         },
#         "task_preference": {
#             "description": "Detailed, systematic projects with clear specifications",
#             "explanation": "Your preference for detailed tasks suggests you excel in roles requiring precision and thoroughness."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=A (minimal interactions), Q4=B (creative)
#     "AAAB": {
#         "work_style": {
#             "description": "Structured creative work with independent execution",
#             "explanation": "You prefer a structured schedule but enjoy creative tasks that can be accomplished independently."
#         },
#         "environment": {
#             "description": "Quiet, private workspace that allows creative thinking",
#             "explanation": "Your preference for quiet spaces combined with creative tasks suggests you need solitude for innovative thinking."
#         },
#         "interaction_level": {
#             "description": "Limited collaboration primarily for feedback on creative output",
#             "explanation": "You work best with minimal interactions, using collaborations mainly to refine your creative ideas."
#         },
#         "task_preference": {
#             "description": "Creative projects with clear boundaries and timelines",
#             "explanation": "You excel at innovative work that still has defined parameters and structure."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=A (minimal), Q4=C (balance)
#     "AAAC": {
#         "work_style": {
#             "description": "Structured work with balanced task variety",
#             "explanation": "You thrive with a structured schedule while enjoying a mix of detailed and creative tasks."
#         },
#         "environment": {
#             "description": "Quiet workspace with areas for different types of work",
#             "explanation": "Your preference for quiet spaces that can accommodate varied work types indicates a need for an adaptable yet private environment."
#         },
#         "interaction_level": {
#             "description": "Primarily independent work with occasional targeted collaboration",
#             "explanation": "You prefer minimal interactions while still participating in collaboration when required for specific tasks."
#         },
#         "task_preference": {
#             "description": "Mixed projects that combine analytical and creative elements",
#             "explanation": "Your preference for balanced tasks suggests you enjoy work that engages both analytical and creative thinking."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=B (comfortable with teamwork), Q4=A (detailed)
#     "AABA": {
#         "work_style": {
#             "description": "Structured collaborative work with focus on details",
#             "explanation": "You thrive with a structured schedule while comfortably engaging in regular teamwork on detailed projects."
#         },
#         "environment": {
#             "description": "Quiet team environment with spaces for focused work",
#             "explanation": "Your preference for quiet spaces combined with comfort in teamwork suggests an environment that balances collaboration and focus."
#         },
#         "interaction_level": {
#             "description": "Regular, structured team interactions around specific tasks",
#             "explanation": "You work well with regular teamwork that has clear purposes and defined communication channels."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects that benefit from team input",
#             "explanation": "You excel at detail-focused work that incorporates perspectives from collaborative efforts."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=B (teamwork), Q4=B (creative)
#     "AABB": {
#         "work_style": {
#             "description": "Structured creative collaboration",
#             "explanation": "You thrive in a structured schedule while comfortably engaging in team-based creative work."
#         },
#         "environment": {
#             "description": "Quiet collaborative space for creative teamwork",
#             "explanation": "Your preference suggests a need for a calm collaborative space where teams can engage in creative processes without excess noise."
#         },
#         "interaction_level": {
#             "description": "Regular creative collaboration with clear communication protocols",
#             "explanation": "You value teamwork for creative endeavors but prefer it happens within structured interaction patterns."
#         },
#         "task_preference": {
#             "description": "Creative projects enhanced through team contribution",
#             "explanation": "You excel at creative work that benefits from multiple perspectives while maintaining clear direction."
#         }
#     },
    
#     # Continuing with the first 6 combinations... (I'll create all 36 combinations)
    
#     # Q1=A (structured), Q2=A (quiet), Q3=B (teamwork), Q4=C (balance)
#     "AABC": {
#         "work_style": {
#             "description": "Structured collaborative work with diverse tasks",
#             "explanation": "You thrive with a structured schedule in a team environment that balances detailed and creative work."
#         },
#         "environment": {
#             "description": "Quiet team space designed for varied collaborative activities",
#             "explanation": "Your preferences suggest a need for a calm environment that supports different types of teamwork."
#         },
#         "interaction_level": {
#             "description": "Regular team engagement across various project aspects",
#             "explanation": "You work well with consistent team interaction that spans both analytical and creative elements."
#         },
#         "task_preference": {
#             "description": "Balanced projects that leverage team strengths in different areas",
#             "explanation": "You excel at work that combines team input on both detailed and creative elements."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=C (leading teams), Q4=A (detailed)
#     "AACA": {
#         "work_style": {
#             "description": "Structured leadership focused on detailed execution",
#             "explanation": "You thrive with a structured schedule while leading teams that focus on precise, detailed work."
#         },
#         "environment": {
#             "description": "Quiet, organized team environment with clear focus areas",
#             "explanation": "Your preferences indicate a need for a calm workspace where you can direct team efforts on detailed work."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions focused on precision and quality",
#             "explanation": "You enjoy coordinating teams with an emphasis on detailed execution and high standards."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects requiring coordinated team effort",
#             "explanation": "You excel at managing complex, detail-focused initiatives that require team coordination."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=C (leading), Q4=B (creative)
#     "AACB": {
#         "work_style": {
#             "description": "Structured creative leadership",
#             "explanation": "You thrive with a structured schedule while leading teams in creative and innovative work."
#         },
#         "environment": {
#             "description": "Quiet, inspiring workspace for creative direction",
#             "explanation": "Your preferences indicate a need for a calm environment where you can guide creative team processes."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions focused on innovation",
#             "explanation": "You enjoy directing teams with an emphasis on creative development and ideation."
#         },
#         "task_preference": {
#             "description": "Creative projects requiring coordinated team innovation",
#             "explanation": "You excel at guiding teams through creative challenges that benefit from structured leadership."
#         }
#     },
    
#     # Q1=A (structured), Q2=A (quiet), Q3=C (leading), Q4=C (balance)
#     "AACC": {
#         "work_style": {
#             "description": "Structured leadership with balanced project focus",
#             "explanation": "You thrive with a structured schedule while leading teams across both analytical and creative work."
#         },
#         "environment": {
#             "description": "Quiet, versatile workspace for multifaceted leadership",
#             "explanation": "Your preferences indicate a need for a calm environment where you can direct diverse team activities."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions across various work domains",
#             "explanation": "You enjoy coordinating teams with flexibility to address both detailed and creative challenges."
#         },
#         "task_preference": {
#             "description": "Balanced projects requiring cohesive team coordination",
#             "explanation": "You excel at guiding teams through complex initiatives that require both analytical and creative approaches."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=A (minimal interactions), Q4=A (detailed)
#     "ABAA": {
#         "work_style": {
#             "description": "Structured, independent work in a collaborative setting",
#             "explanation": "You thrive with a structured schedule while focusing on detailed work, despite being in a collaborative space."
#         },
#         "environment": {
#             "description": "Collaborative environment with personal focus zones",
#             "explanation": "You prefer collaborative spaces but need dedicated areas for concentrated individual work."
#         },
#         "interaction_level": {
#             "description": "Minimal direct interaction with awareness of team context",
#             "explanation": "You prefer limited personal interactions while still being part of a collaborative environment."
#         },
#         "task_preference": {
#             "description": "Detail-oriented independent contributions to team projects",
#             "explanation": "You excel at focused, precise work that feeds into broader team objectives."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=A (minimal interactions), Q4=B (creative)
#     "ABAB": {
#         "work_style": {
#             "description": "Structured creative work with independent execution in team settings",
#             "explanation": "You thrive with a structured schedule and creative focus, preferring to work independently despite being in collaborative spaces."
#         },
#         "environment": {
#             "description": "Creative collaborative environment with personal work areas",
#             "explanation": "You prefer collaborative spaces that foster creativity but need your own zone for focused creative work."
#         },
#         "interaction_level": {
#             "description": "Limited collaboration with creative exchange",
#             "explanation": "You prefer minimal interactions while still benefiting from creative inspiration in team environments."
#         },
#         "task_preference": {
#             "description": "Creative projects with independent execution in team context",
#             "explanation": "You excel at creative work that allows you to contribute your unique vision to broader team initiatives."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=A (minimal), Q4=C (balance)
#     "ABAC": {
#         "work_style": {
#             "description": "Structured independent work with varied focus in team settings",
#             "explanation": "You thrive with a structured schedule and balanced task types, working independently in collaborative environments."
#         },
#         "environment": {
#             "description": "Versatile collaborative environment with dedicated focus space",
#             "explanation": "You prefer collaborative settings that can accommodate your varied work while providing space for concentration."
#         },
#         "interaction_level": {
#             "description": "Minimal but purposeful team interactions across work types",
#             "explanation": "You prefer limited interactions that support your diverse work contributions in a team context."
#         },
#         "task_preference": {
#             "description": "Balanced projects with independent execution in team framework",
#             "explanation": "You excel at work that blends analytical and creative elements while allowing autonomous contribution."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=B (team), Q4=A (detailed)
#     "ABBA": {
#         "work_style": {
#             "description": "Structured, collaborative work with detail focus",
#             "explanation": "You thrive with a structured schedule in open team environments focused on detailed execution."
#         },
#         "environment": {
#             "description": "Collaborative workspace optimized for focused teamwork",
#             "explanation": "Your preferences indicate a need for open, interactive spaces that still enable concentrated collaboration."
#         },
#         "interaction_level": {
#             "description": "Regular team engagement on detailed initiatives",
#             "explanation": "You work well with consistent team interaction centered around precision and quality."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with collaborative execution",
#             "explanation": "You excel at precise work that incorporates active team input and coordination."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=B (team), Q4=B (creative)
#     "ABBB": {
#         "work_style": {
#             "description": "Structured creative collaboration",
#             "explanation": "You thrive with a structured schedule in team environments focused on creative and innovative work."
#         },
#         "environment": {
#             "description": "Dynamic collaborative workspace for creative teamwork",
#             "explanation": "Your preferences indicate a need for interactive spaces that foster creative exchange and collaboration."
#         },
#         "interaction_level": {
#             "description": "Active creative collaboration with clear process",
#             "explanation": "You work well with regular team interaction centered around innovation and creative development."
#         },
#         "task_preference": {
#             "description": "Creative projects with collaborative execution",
#             "explanation": "You excel at innovative work that leverages team synergy within a structured framework."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=B (team), Q4=C (balance)
#     "ABBC": {
#         "work_style": {
#             "description": "Structured team collaboration across varied tasks",
#             "explanation": "You thrive with a structured schedule in collaborative settings that involve both detailed and creative work."
#         },
#         "environment": {
#             "description": "Versatile collaborative workspace for multifaceted teamwork",
#             "explanation": "Your preferences indicate a need for team environments that support different types of collaborative activities."
#         },
#         "interaction_level": {
#             "description": "Regular team engagement across diverse work elements",
#             "explanation": "You work well with consistent collaboration that addresses both analytical and creative aspects of projects."
#         },
#         "task_preference": {
#             "description": "Balanced projects with integrated team execution",
#             "explanation": "You excel at work that combines detailed and creative elements through cohesive team effort."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=C (leading), Q4=A (detailed)
#     "ABCA": {
#         "work_style": {
#             "description": "Structured leadership in collaborative settings with detail focus",
#             "explanation": "You thrive with a structured schedule while leading teams in open environments focused on detailed work."
#         },
#         "environment": {
#             "description": "Collaborative workspace designed for precision-focused leadership",
#             "explanation": "Your preferences indicate a need for interactive environments where you can direct detailed team efforts."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions in collaborative detailed work",
#             "explanation": "You enjoy coordinating teams in open settings with an emphasis on precision and quality."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects requiring coordinated team collaboration",
#             "explanation": "You excel at managing complex, detail-focused initiatives in highly interactive team contexts."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=C (leading), Q4=B (creative)
#     "ABCB": {
#         "work_style": {
#             "description": "Structured creative leadership in collaborative settings",
#             "explanation": "You thrive with a structured schedule while leading teams in open environments focused on creative work."
#         },
#         "environment": {
#             "description": "Dynamic collaborative workspace for creative leadership",
#             "explanation": "Your preferences indicate a need for interactive environments where you can direct innovative team efforts."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions in collaborative creative work",
#             "explanation": "You enjoy coordinating teams in open settings with an emphasis on innovation and creativity."
#         },
#         "task_preference": {
#             "description": "Creative projects requiring coordinated team collaboration",
#             "explanation": "You excel at managing innovative initiatives that harness collective creativity through structured guidance."
#         }
#     },
    
#     # Q1=A (structured), Q2=B (collaborative), Q3=C (leading), Q4=C (balance)
#     "ABCC": {
#         "work_style": {
#             "description": "Structured versatile leadership in collaborative settings",
#             "explanation": "You thrive with a structured schedule while leading teams in open environments across diverse work types."
#         },
#         "environment": {
#             "description": "Adaptable collaborative workspace for multifaceted leadership",
#             "explanation": "Your preferences indicate a need for interactive environments where you can direct varied team activities."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions spanning work domains",
#             "explanation": "You enjoy coordinating teams in open settings with flexibility across analytical and creative projects."
#         },
#         "task_preference": {
#             "description": "Balanced projects requiring versatile team coordination",
#             "explanation": "You excel at guiding teams through initiatives that blend detailed and creative elements in collaborative contexts."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=A (minimal), Q4=A (detailed)
#     "BAAA": {
#         "work_style": {
#             "description": "Flexible, independent work with detail focus",
#             "explanation": "You thrive with flexible hours while focusing on detailed work in quiet environments."
#         },
#         "environment": {
#             "description": "Quiet workspace with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm environment with flexible work arrangements."
#         },
#         "interaction_level": {
#             "description": "Minimal interactions with schedule autonomy",
#             "explanation": "You prefer limited social engagement and the freedom to manage your own workflow."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with flexible execution",
#             "explanation": "You excel at precision work when allowed to approach it with your own timing and rhythm."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=A (minimal), Q4=B (creative)
#     "BAAB": {
#         "work_style": {
#             "description": "Flexible, independent creative work",
#             "explanation": "You thrive with flexible hours while focusing on creative projects in quiet environments."
#         },
#         "environment": {
#             "description": "Quiet, inspirational space with flexible scheduling",
#             "explanation": "Your preferences indicate a need for a calm, creativity-conducive environment with adaptable work hours."
#         },
#         "interaction_level": {
#             "description": "Minimal interactions with autonomous creative process",
#             "explanation": "You prefer limited social engagement while having freedom to manage your creative workflow."
#         },
#         "task_preference": {
#             "description": "Creative projects with flexible, independent execution",
#             "explanation": "You excel at innovative work when allowed to approach it at your own pace and in your own way."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=A (minimal), Q4=C (balance)
#     "BAAC": {
#         "work_style": {
#             "description": "Flexible, independent work with varied focus",
#             "explanation": "You thrive with flexible hours while working on diverse tasks in quiet environments."
#         },
#         "environment": {
#             "description": "Quiet, versatile space with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm environment that supports different work types and flexible timing."
#         },
#         "interaction_level": {
#             "description": "Minimal interactions with workflow autonomy",
#             "explanation": "You prefer limited social engagement while having freedom to manage varied work types."
#         },
#         "task_preference": {
#             "description": "Balanced projects with flexible, independent execution",
#             "explanation": "You excel at work that combines analytical and creative elements when allowed to approach it on your own terms."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=B (team), Q4=A (detailed)
#     "BABA": {
#         "work_style": {
#             "description": "Flexible team collaboration with detail focus in quiet settings",
#             "explanation": "You thrive with flexible hours while working on detailed projects with teams in calm environments."
#         },
#         "environment": {
#             "description": "Quiet collaborative space with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm team environment that allows for flexible work arrangements."
#         },
#         "interaction_level": {
#             "description": "Regular team interaction with flexible coordination",
#             "explanation": "You work well with consistent teamwork that accommodates variable scheduling and rhythms."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with flexible team execution",
#             "explanation": "You excel at precision work that incorporates team input while allowing for adaptable approaches."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=B (team), Q4=B (creative)
#     "BABB": {
#         "work_style": {
#             "description": "Flexible creative collaboration in quiet settings",
#             "explanation": "You thrive with flexible hours while working on creative projects with teams in calm environments."
#         },
#         "environment": {
#             "description": "Quiet creative team space with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm, creativity-conducive team environment with flexible arrangements."
#         },
#         "interaction_level": {
#             "description": "Regular creative collaboration with flexible coordination",
#             "explanation": "You work well with team-based creativity that accommodates variable timing and approaches."
#         },
#         "task_preference": {
#             "description": "Creative projects with flexible team execution",
#             "explanation": "You excel at innovative work that harnesses team synergy while allowing for adaptable processes."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=B (team), Q4=C (balance)
#     "BABC": {
#         "work_style": {
#             "description": "Flexible team collaboration across varied tasks in quiet settings",
#             "explanation": "You thrive with flexible hours while working on diverse projects with teams in calm environments."
#         },
#         "environment": {
#             "description": "Quiet versatile team space with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm team environment that supports different work types and flexible timing."
#         },
#         "interaction_level": {
#             "description": "Regular team engagement across work domains with flexible coordination",
#             "explanation": "You work well with consistent teamwork that spans analytical and creative elements while accommodating variable schedules."
#         },
#         "task_preference": {
#             "description": "Balanced projects with flexible team execution",
#             "explanation": "You excel at work that combines detailed and creative elements through team effort with adaptable approaches."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=C (leading), Q4=A (detailed)
#     "BACA": {
#         "work_style": {
#             "description": "Flexible leadership focused on detailed execution in quiet settings",
#             "explanation": "You thrive with flexible hours while leading teams on detailed projects in calm environments."
#         },
#         "environment": {
#             "description": "Quiet, organized space for team direction with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm leadership environment that enables flexible work coordination."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions with flexible coordination",
#             "explanation": "You enjoy directing teams with an emphasis on detail while accommodating variable scheduling and approaches."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with flexible team leadership",
#             "explanation": "You excel at guiding precise, detailed initiatives while allowing for adaptable execution methods."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=C (leading), Q4=B (creative)
#     "BACB": {
#         "work_style": {
#             "description": "Flexible creative leadership in quiet settings",
#             "explanation": "You thrive with flexible hours while leading teams on creative projects in calm environments."
#         },
#         "environment": {
#             "description": "Quiet, inspiring space for creative direction with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for a calm leadership environment that fosters innovation with flexible coordination."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions in creative domains with flexible approaches",
#             "explanation": "You enjoy directing teams with an emphasis on creativity while accommodating variable rhythms and methods."
#         },
#         "task_preference": {
#             "description": "Creative projects with flexible team leadership",
#             "explanation": "You excel at guiding innovative initiatives while allowing for adaptable creative processes."
#         }
#     },
    
#     # Q1=B (flexible), Q2=A (quiet), Q3=C (leading), Q4=C (balance)
#     "BACC": {
#         "work_style": {
#             "description": "Flexible versatile leadership in quiet settings",
#             "explanation": "You thrive with flexible hours while leading teams across diverse work types in calm environments."
#         },
#         "environment": {
#             "description": "Quiet, adaptable space for varied team direction",
#             "explanation": "Your preferences indicate a need for a calm leadership environment that supports different work types with flexible coordination."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions across work domains with flexible approaches",
#             "explanation": "You enjoy directing teams with versatility across analytical and creative projects while accommodating variable methods."
#         },
#         "task_preference": {
#             "description": "Balanced projects with flexible team leadership",
#             "explanation": "You excel at guiding initiatives that blend detailed and creative elements through adaptable direction styles."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=C (leading), Q4=C (balance)
#     "BBCC": {
#         "work_style": {
#             "description": "Adaptable team leadership with balanced approach",
#             "explanation": "You thrive in flexible environments where you can lead teams through diverse projects requiring both analytical and creative thinking."
#         },
#         "environment": {
#             "description": "Collaborative, dynamic workspace supporting various work modes",
#             "explanation": "Your preferences indicate a need for an interactive environment that can adapt to different types of team activities."
#         },
#         "interaction_level": {
#             "description": "High engagement leadership across diverse team functions",
#             "explanation": "You enjoy directing teams with a balanced approach to both structured and creative collaboration."
#         },
#         "task_preference": {
#             "description": "Versatile projects that leverage collective team strengths",
#             "explanation": "You excel at guiding teams through work that requires both analytical rigor and creative innovation."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=A (minimal), Q4=A (detailed)
#     "BBAA": {
#         "work_style": {
#             "description": "Flexible, detailed work with limited interaction in collaborative settings",
#             "explanation": "You thrive with flexible hours while focusing on detailed work, preferring minimal direct engagement despite collaborative spaces."
#         },
#         "environment": {
#             "description": "Open, dynamic workspace with personal focus options",
#             "explanation": "Your preferences indicate a need for collaborative environments that still allow you to work independently with flexible timing."
#         },
#         "interaction_level": {
#             "description": "Limited direct engagement in collaborative spaces",
#             "explanation": "You prefer minimal personal interaction while still benefiting from the energy of collaborative environments."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with flexible, independent execution",
#             "explanation": "You excel at precision work when allowed to approach it with your own timing in collaborative contexts."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=A (minimal), Q4=B (creative)
#     "BBAB": {
#         "work_style": {
#             "description": "Flexible, creative work with limited interaction in collaborative settings",
#             "explanation": "You thrive with flexible hours while focusing on creative work, preferring minimal direct engagement despite collaborative spaces."
#         },
#         "environment": {
#             "description": "Inspirational, dynamic workspace with personal creative zones",
#             "explanation": "Your preferences indicate a need for stimulating environments that still allow you to create independently with flexible timing."
#         },
#         "interaction_level": {
#             "description": "Limited direct engagement with creative observation",
#             "explanation": "You prefer minimal personal interaction while still drawing inspiration from collaborative creative environments."
#         },
#         "task_preference": {
#             "description": "Creative projects with flexible, independent execution",
#             "explanation": "You excel at innovative work when allowed to approach it with your own method and timing in stimulating contexts."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=A (minimal), Q4=C (balance)
#     "BBAC": {
#         "work_style": {
#             "description": "Flexible, varied work with limited interaction in collaborative settings",
#             "explanation": "You thrive with flexible hours while focusing on diverse work types, preferring minimal direct engagement despite collaborative spaces."
#         },
#         "environment": {
#             "description": "Versatile, dynamic workspace with personal focus options",
#             "explanation": "Your preferences indicate a need for stimulating environments that accommodate different work while allowing independent execution."
#         },
#         "interaction_level": {
#             "description": "Limited direct engagement with contextual awareness",
#             "explanation": "You prefer minimal personal interaction while still benefiting from the diverse influences of collaborative environments."
#         },
#         "task_preference": {
#             "description": "Balanced projects with flexible, independent execution",
#             "explanation": "You excel at work combining analytical and creative elements when approached with your own timing in dynamic contexts."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=B (team), Q4=A (detailed)
#     "BBBA": {
#         "work_style": {
#             "description": "Flexible team collaboration with detail focus",
#             "explanation": "You thrive with flexible hours while working on detailed projects collaboratively in interactive environments."
#         },
#         "environment": {
#             "description": "Dynamic team workspace with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for active, collaborative environments that accommodate flexible team coordination."
#         },
#         "interaction_level": {
#             "description": "Regular team engagement with flexible coordination",
#             "explanation": "You enjoy consistent collaboration that adapts to variable schedules and work approaches."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with flexible team execution",
#             "explanation": "You excel at precision work that incorporates team synergy with adaptable methods and timing."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=B (team), Q4=B (creative)
#     "BBBB": {
#         "work_style": {
#             "description": "Flexible creative collaboration",
#             "explanation": "You thrive with flexible hours while working on creative projects collaboratively in interactive environments."
#         },
#         "environment": {
#             "description": "Dynamic creative workspace with adaptable team settings",
#             "explanation": "Your preferences indicate a need for stimulating, collaborative environments that foster creativity with flexible coordination."
#         },
#         "interaction_level": {
#             "description": "Active creative collaboration with flexible approaches",
#             "explanation": "You enjoy engaging team interaction centered on innovation with adaptable methods and timing."
#         },
#         "task_preference": {
#             "description": "Creative projects with flexible collaborative execution",
#             "explanation": "You excel at innovative work that harnesses collective creativity through adaptable team processes."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=B (team), Q4=C (balance)
#     "BBBC": {
#         "work_style": {
#             "description": "Flexible team collaboration across varied tasks",
#             "explanation": "You thrive with flexible hours while working on diverse projects collaboratively in interactive environments."
#         },
#         "environment": {
#             "description": "Versatile team workspace with adaptable scheduling",
#             "explanation": "Your preferences indicate a need for dynamic environments that support different work types with flexible team coordination."
#         },
#         "interaction_level": {
#             "description": "Regular team engagement across work domains with flexible approaches",
#             "explanation": "You enjoy consistent collaboration spanning analytical and creative elements with adaptable coordination."
#         },
#         "task_preference": {
#             "description": "Balanced projects with flexible collaborative execution",
#             "explanation": "You excel at work that combines detailed and creative elements through adaptable team processes."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=C (leading), Q4=A (detailed)
#     "BBCA": {
#         "work_style": {
#             "description": "Flexible leadership with detail focus in collaborative settings",
#             "explanation": "You thrive with flexible hours while leading teams on detailed projects in interactive environments."
#         },
#         "environment": {
#             "description": "Dynamic workspace optimized for detailed team leadership",
#             "explanation": "Your preferences indicate a need for collaborative environments where you can direct precision-focused work with flexible coordination."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions in detailed domains with flexible approaches",
#             "explanation": "You enjoy directing teams with an emphasis on precision while accommodating variable methods and schedules."
#         },
#         "task_preference": {
#             "description": "Detail-oriented projects with flexible team direction",
#             "explanation": "You excel at guiding teams through precise initiatives with adaptable leadership approaches."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=C (leading), Q4=B (creative)
#     "BBCB": {
#         "work_style": {
#             "description": "Flexible creative leadership in collaborative settings",
#             "explanation": "You thrive with flexible hours while leading teams on creative projects in interactive environments."
#         },
#         "environment": {
#             "description": "Dynamic workspace optimized for creative team leadership",
#             "explanation": "Your preferences indicate a need for collaborative environments where you can direct innovative work with flexible coordination."
#         },
#         "interaction_level": {
#             "description": "Leadership-oriented interactions in creative domains with flexible approaches",
#             "explanation": "You enjoy directing teams with an emphasis on creativity while accommodating variable methods and schedules."
#         },
#         "task_preference": {
#             "description": "Creative projects with flexible team direction",
#             "explanation": "You excel at guiding teams through innovative initiatives with adaptable leadership approaches."
#         }
#     },
    
#     # Q1=B (flexible), Q2=B (collaborative), Q3=C (leading), Q4=C (balance)
#     "BBCC": {
#         "work_style": {
#             "description": "Adaptable team leadership with balanced approach",
#             "explanation": "You thrive in flexible environments where you can lead teams through diverse projects requiring both analytical and creative thinking."
#         },
#         "environment": {
#             "description": "Collaborative, dynamic workspace supporting various work modes",
#             "explanation": "Your preferences indicate a need for an interactive environment that can adapt to different types of team activities."
#         },
#         "interaction_level": {
#             "description": "High engagement leadership across diverse team functions",
#             "explanation": "You enjoy directing teams with a balanced approach to both structured and creative collaboration."
#         },
#         "task_preference": {
#             "description": "Versatile projects that leverage collective team strengths",
#             "explanation": "You excel at guiding teams through work that requires both analytical rigor and creative innovation."
#         }
#     }
# }

# Helper function to get analysis for a specific combination of answers
def get_analysis_for_combination(q1, q2, q3, q4):
    """
    Get the pre-computed analysis for a specific combination of answers from DynamoDB.
    
    Args:
        q1, q2, q3, q4: The answer options (A, B, C) for the first 4 questions
        
    Returns:
        The pre-computed analysis for that combination, or None if not found
    """
    template_id = q1 + q2 + q3 + q4
    
    try:
        # Query DynamoDB for the template
        response = table.get_item(Key={'template_id': template_id})
        
        # Check if the item exists
        if 'Item' in response:
            return response['Item']
        else:
            print(f"Template {template_id} not found in DynamoDB")
            return None
    except Exception as e:
        print(f"Error retrieving template from DynamoDB: {str(e)}")
        # Fallback to local templates if DynamoDB access fails
        return None

import boto3
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('AnalysisTemplates')

# Step 1: Clear all existing items
def clear_table():
    print("Clearing existing items...")
    response = table.scan()
    data = response.get('Items', [])

    with table.batch_writer() as batch:
        for item in data:
            batch.delete_item(Key={'template_id': item['template_id']})
    print(f"Deleted {len(data)} item(s).")

# Step 2: Insert new cleaned data (assumes analysis_templates is defined above)
def insert_templates(data):
    print("Inserting new items...")
    with table.batch_writer() as batch:
        for template_id, content in data.items():
            batch.put_item(
                Item={
                    'template_id': template_id,
                    'work_style': {
                        'description': content['work_style']['description'],
                        'explanation': content['work_style']['explanation']
                    },
                    'environment': {
                        'description': content['environment']['description'],
                        'explanation': content['environment']['explanation']
                    },
                    'interaction_level': {
                        'description': content['interaction_level']['description'],
                        'explanation': content['interaction_level']['explanation']
                    },
                    'task_preference': {
                        'description': content['task_preference']['description'],
                        'explanation': content['task_preference']['explanation']
                    }
                }
            )
    print("Insert complete.")

# Run
# clear_table()
# insert_templates(analysis_templates)
