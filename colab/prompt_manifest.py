"""Luna Avatar Generation - Master Prompt Manifest.

Consolidates all prompts into a deduplicated master list with:
- Regular outfit prompts (107 base) x 4 hairstyle variants = 428 per applicable outfit
- Costume-specific prompts (3-5 per costume, NOT multiplied by hairstyles)
- Luna creative additions (new hairstyles, accessories, moon-themed touches)
- Full cross-product of every prompt x every applicable base image

This file is imported by the Colab notebook to drive batch generation.

Usage:
    from prompt_manifest import MANIFEST, BASE_IMAGES, MASTER_PROMPTS
    print(f'{len(MANIFEST)} total image combinations')

Author: PyAgentVox
"""

from __future__ import annotations

# ============================================================================
# BASE IMAGES
# ============================================================================
# 23 reference images (9 regular outfits + 14 costumes).
#
# Character: Auburn/chestnut wavy hair, green eyes, round glasses,
#            crescent moon necklace, crescent moon earrings, fair skin.

BASE_IMAGES: dict[str, dict] = {
    # ── REGULAR OUTFITS ──────────────────────────────────────────────
    'dress': {
        'file': 'dress.jpg',
        'outfit_key': 'dress',
        'category': 'regular',
        'description': 'Cream puff-sleeve V-neck dress with belt, glasses, hair down and wavy',
        'hair': 'long wavy auburn hair down',
    },
    'sundress': {
        'file': 'sundress.jpg',
        'outfit_key': 'sundress',
        'category': 'regular',
        'description': 'Cream spaghetti-strap sundress with scalloped neckline, glasses, hair down',
        'hair': 'long wavy auburn hair down',
    },
    'croptop': {
        'file': 'croptop.webp',
        'outfit_key': 'croptop',
        'category': 'regular',
        'description': 'White tied crop top, beach setting, sunglasses, pina colada, hair down',
        'hair': 'long wavy auburn hair down',
    },
    'hoodie': {
        'file': 'hoodie.jpg',
        'outfit_key': 'hoodie',
        'category': 'regular',
        'description': 'Beige/tan hoodie with dark pants, hair in side ponytail',
        'hair': 'auburn hair in side ponytail',
    },
    'daisy-dukes': {
        'file': 'daisy-dukes.jpg',
        'outfit_key': 'dukes',
        'category': 'regular',
        'description': 'Dark tank top with denim shorts, sun hat, sunglasses, cocktail, hair down',
        'hair': 'long wavy auburn hair down',
    },
    'swimsuit': {
        'file': 'swimsuit.jpg',
        'outfit_key': 'swimsuit',
        'category': 'regular',
        'description': 'Dark tank top and denim shorts, sun hat, sunglasses, cocktail, hair down flowing',
        'hair': 'long wavy auburn hair down and flowing',
    },
    'ball-gown': {
        'file': 'ball-gown.jpg',
        'outfit_key': 'formal',
        'category': 'regular',
        'description': 'Emerald green sparkly ball gown with spaghetti straps, hair down elegant',
        'hair': 'long wavy auburn hair down, elegant styling',
    },
    'pajamas': {
        'file': 'pajamas.jpg',
        'outfit_key': 'pajamas',
        'category': 'regular',
        'description': 'Cream button-up pajama shorts set with dark piping, hair in messy bun',
        'hair': 'auburn hair in messy bun',
    },
    'teacher': {
        'file': 'teacher.jpg',
        'outfit_key': 'teaching',
        'category': 'regular',
        'description': 'Black blazer over cream top with black skirt, crystal earrings, hair in professional bun',
        'hair': 'auburn hair in professional bun',
    },

    # ── COSTUMES ─────────────────────────────────────────────────────
    'knight-heavy': {
        'file': 'costume-knight.jpg',
        'outfit_key': 'knight',
        'category': 'costume',
        'description': 'Full plate armor with moon engravings, sword, moon shield, hair down flowing',
        'hair': 'long wavy auburn hair flowing under armor',
    },
    'knight-light': {
        'file': 'costume-knight.webp',
        'outfit_key': 'knight',
        'category': 'costume',
        'description': 'Light armor with skirt, moon shield, shin guards, forehead circlet, hair down',
        'hair': 'long wavy auburn hair with forehead circlet',
    },
    'cowgirl': {
        'file': 'costume-cowgirl.webp',
        'outfit_key': 'cowgirl',
        'category': 'costume',
        'description': 'Cowboy hat, bandana around neck, revolvers at hips, western vest and shorts',
        'hair': 'long wavy auburn hair under cowboy hat',
    },
    'cyberpunk': {
        'file': 'costume-cyberpunk.jpg',
        'outfit_key': 'cyberpunk',
        'category': 'costume',
        'description': 'Black leather jacket, neon accents, cybernetic arm, tech glasses, futuristic',
        'hair': 'long wavy auburn hair with neon highlights',
    },
    'pirate': {
        'file': 'costume-pirate.jpg',
        'outfit_key': 'pirate',
        'category': 'costume',
        'description': 'Tricorn hat, flintlock pistol, hook hand, parrot on shoulder, off-shoulder blouse',
        'hair': 'long wavy auburn hair under tricorn hat',
    },
    'detective': {
        'file': 'costume-detective.webp',
        'outfit_key': 'detective',
        'category': 'costume',
        'description': 'Deerstalker cap, tan trench coat, magnifying glass, cream blouse, glasses',
        'hair': 'long wavy auburn hair under deerstalker cap',
    },
    'elf': {
        'file': 'costume-elf.webp',
        'outfit_key': 'elf',
        'category': 'costume',
        'description': 'Pointed elf ears, dark green sparkly robes with gold trim, hands clasped',
        'hair': 'long wavy auburn hair, elvish styling',
    },
    'goth': {
        'file': 'costume-goth.jpg',
        'outfit_key': 'goth',
        'category': 'costume',
        'description': 'Black lipstick, black lace dress, rose vine tattoos on both arms, glasses, moon earrings',
        'hair': 'long wavy dark auburn hair, goth styling',
    },
    'mad-scientist': {
        'file': 'costume-mad-scientist.jpg',
        'outfit_key': 'scientist',
        'category': 'costume',
        'description': 'Lab coat, glasses, pouring flask into test tube, green liquid, manic grin',
        'hair': 'auburn hair half-up messy with loose strands',
    },
    'superhero': {
        'file': 'costume-superhero.jpg',
        'outfit_key': 'superhero',
        'category': 'costume',
        'description': 'Silver/white bodysuit with crescent moon emblem, cape, gloves, spaghetti straps',
        'hair': 'long wavy auburn hair flowing heroically',
    },
    'superhero2': {
        'file': 'costume-superhero2.jpg',
        'outfit_key': 'superhero',
        'category': 'costume',
        'description': 'Silver/white bodysuit with crescent moon emblem, high collar cape, close-up',
        'hair': 'long wavy auburn hair flowing',
    },
    'vampire': {
        'file': 'costume-vampire.webp',
        'outfit_key': 'vampire',
        'category': 'costume',
        'description': 'Black dress, vampire cape held open by both hands, fanged smile, no glasses',
        'hair': 'long wavy auburn hair, vampiric styling',
    },
    'witch': {
        'file': 'costume-witch.webp',
        'outfit_key': 'witch',
        'category': 'costume',
        'description': 'Wide-brimmed witch hat, black sparkly dress, magic wand with sparkle trail, glasses',
        'hair': 'long wavy auburn hair under witch hat',
    },
    'construction': {
        'file': 'costume-construction.jpg',
        'outfit_key': 'construction',
        'category': 'costume',
        'description': 'Yellow hard hat, orange safety vest, tool belt with hammer, work gloves, glasses',
        'hair': 'long wavy auburn hair under hard hat',
    },
}


# ============================================================================
# PROMPT CLASS
# ============================================================================

class Prompt:
    """A single pose/emotion prompt entry."""

    __slots__ = ('text', 'emotion', 'tags', 'filename_hint', 'outfit_filter', 'is_costume', 'hairstyle_variant')

    def __init__(
        self,
        text: str,
        emotion: str,
        tags: list[str],
        filename_hint: str,
        outfit_filter: list[str] | None = None,
        is_costume: bool = False,
        hairstyle_variant: str | None = None,
    ):
        self.text = text
        self.emotion = emotion
        self.tags = tags
        self.filename_hint = filename_hint
        self.outfit_filter = outfit_filter
        self.is_costume = is_costume
        self.hairstyle_variant = hairstyle_variant

    def applies_to(self, base_key: str) -> bool:
        """Check if this prompt should be applied to a given base image."""
        if self.outfit_filter is None:
            return True
        return base_key in self.outfit_filter


# ============================================================================
# HAIRSTYLE VARIANTS
# ============================================================================
# Each regular prompt is multiplied by these 4 hairstyle variants.
# Costume prompts are NOT multiplied (costumes have specific hair situations).

HAIRSTYLE_VARIANTS: list[dict[str, str]] = [
    {'suffix': '', 'modifier': '', 'tag': 'hair-down'},
    {'suffix': '-bun', 'modifier': ', with messy bun hairstyle', 'tag': 'messy-bun'},
    {'suffix': '-ponytail', 'modifier': ', with straight ponytail hairstyle', 'tag': 'ponytail'},
    {'suffix': '-braid', 'modifier': ', with big loose braid hairstyle', 'tag': 'braid'},
]


# ============================================================================
# REGULAR OUTFIT PROMPTS (107 base prompts)
# ============================================================================
# These get multiplied by 4 hairstyle variants in build_manifest().

# fmt: off
_REGULAR_PROMPTS: list[Prompt] = [
    # ── APOLOGETIC ────────────────────────────────────────────────────
    Prompt(
        'One hand behind head nervously, awkward smile, eyes slightly averted, sheepish apologetic expression',
        'apologetic', ['nervous', 'sheepish', 'awkward'], 'apologetic-nervous',
    ),
    Prompt(
        'Both hands pressed together in apologetic gesture, sorry expression, slightly bowed head, puppy-dog eyes',
        'apologetic', ['sorry', 'pleading', 'bowing'], 'apologetic-sorry',
    ),
    Prompt(
        'One hand scratching back of head sheepishly, nervous smile, "oops I messed up" apologetic energy',
        'apologetic', ['sheepish', 'oops', 'scratching'], 'apologetic-oops',
    ),
    Prompt(
        'Hands clasped together pleadingly, sincere sorry expression, genuine regret in eyes',
        'apologetic', ['pleading', 'clasped-hands', 'regret'], 'apologetic-pleading',
        outfit_filter=['dress', 'sundress'],
    ),
    Prompt(
        'One hand covering mouth in embarrassed "oops" gesture, sheepish smile, bashful apologetic look',
        'apologetic', ['embarrassed', 'bashful', 'oops'], 'apologetic-embarrassed',
    ),
    Prompt(
        'Hand behind neck nervously, uncomfortable apologetic smile, awkward guilty expression',
        'apologetic', ['guilty', 'uncomfortable', 'neck-rub'], 'apologetic-guilty',
    ),

    # ── BORED / WAITING ──────────────────────────────────────────────
    Prompt(
        'Tired bored expression, slight frown, arms crossed or hand propping up head, "waiting forever" energy',
        'bored', ['tired', 'frown', 'impatient'], 'bored-waiting',
    ),

    # ── CALM / NEUTRAL ───────────────────────────────────────────────
    Prompt(
        'Holding coffee mug with both hands, neutral calm expression, peaceful relaxed pose',
        'calm', ['coffee', 'mug', 'peaceful', 'relaxed'], 'calm-coffee-both',
    ),
    Prompt(
        'Holding coffee mug with gentle smile, content warm expression, cozy comfortable energy',
        'warm', ['coffee', 'mug', 'cozy', 'content'], 'warm-coffee-gentle',
    ),
    Prompt(
        'Hands resting on laptop keyboard, neutral expression at screen, calm working pose',
        'calm', ['laptop', 'typing', 'working', 'neutral'], 'calm-laptop-neutral',
    ),
    Prompt(
        'Laptop in front, focused neutral typing, calm concentration',
        'focused', ['laptop', 'typing', 'concentration'], 'focused-laptop-typing',
    ),
    Prompt(
        'Eyes peacefully closed, hands folded or resting, serene meditative calm expression',
        'calm', ['eyes-closed', 'serene', 'meditative', 'peaceful'], 'calm-meditative',
    ),
    Prompt(
        'Hands clasped together peacefully, eyes closed, tranquil serene expression',
        'calm', ['clasped-hands', 'eyes-closed', 'tranquil'], 'calm-tranquil',
    ),
    Prompt(
        'Neutral calm standing pose, slight smile, relaxed peaceful energy',
        'calm', ['standing', 'neutral', 'relaxed', 'slight-smile'], 'calm-standing',
    ),
    Prompt(
        'Calm serene peaceful expression, tranquil relaxed energy',
        'calm', ['serene', 'tranquil', 'relaxed'], 'calm-serene',
    ),

    # ── CHEERFUL ──────────────────────────────────────────────────────
    Prompt(
        'One hand raised in friendly wave, bright cheerful smile, welcoming happy energy',
        'cheerful', ['wave', 'welcoming', 'friendly'], 'cheerful-wave',
    ),
    Prompt(
        'Both hands making peace signs near face, big smile, playful cheerful expression',
        'cheerful', ['peace-sign', 'double', 'playful'], 'cheerful-doublepea',
    ),
    Prompt(
        'Peace sign with both hands, cheerful happy smile, fun positive energy',
        'cheerful', ['peace-sign', 'positive', 'fun'], 'cheerful-peace',
    ),
    Prompt(
        'Cheerful smile with wave gesture, friendly welcoming expression',
        'cheerful', ['wave', 'friendly', 'welcoming'], 'cheerful-friendlywave',
    ),
    Prompt(
        'Cute head tilt with sweet smile, cheerful playful energy, innocent happy look',
        'cheerful', ['head-tilt', 'sweet', 'innocent', 'cute'], 'cheerful-headtilt',
    ),
    Prompt(
        'Sweet happy smile, cheerful friendly expression, warm positive energy',
        'cheerful', ['sweet', 'happy', 'positive'], 'cheerful-sweet',
    ),
    Prompt(
        'Cheerful happy expression, arms out gesture of joy, bright smile',
        'cheerful', ['arms-out', 'joyful', 'bright'], 'cheerful-armsout',
        outfit_filter=['dress', 'sundress', 'daisy-dukes'],
    ),
    Prompt(
        'Warm welcoming smile with open arms gesture, friendly caring expression',
        'warm', ['open-arms', 'welcoming', 'caring'], 'warm-openarms',
    ),

    # ── CURIOUS ───────────────────────────────────────────────────────
    Prompt(
        'Leaning forward with hands behind back, wide-eyed curious expression, inquisitive interested look',
        'curious', ['leaning', 'wide-eyed', 'inquisitive', 'hands-behind'], 'curious-lean',
    ),
    Prompt(
        'Leaning in closer examining something, hands clasped, eager curious expression',
        'curious', ['examining', 'clasped-hands', 'eager'], 'curious-examine',
    ),
    Prompt(
        'Head tilted in curiosity, wondering expression, "what\'s that?" interested look',
        'curious', ['head-tilt', 'wondering', 'interested'], 'curious-tilt',
    ),
    Prompt(
        'Curious questioning expression, one hand near face, intrigued look',
        'curious', ['questioning', 'hand-face', 'intrigued'], 'curious-question',
    ),
    Prompt(
        'Hand raised in questioning gesture, curious wondering expression, "huh?" energy',
        'curious', ['hand-raised', 'wondering', 'huh'], 'curious-huh',
        outfit_filter=['dress', 'sundress'],
    ),

    # ── DETERMINED ────────────────────────────────────────────────────
    Prompt(
        'One fist raised near face, confident determined expression, strong resolute stance',
        'determined', ['fist', 'confident', 'resolute'], 'determined-fist',
    ),
    Prompt(
        'Arms crossed confidently, strong determined smile, self-assured powerful pose',
        'determined', ['arms-crossed', 'confident', 'powerful'], 'determined-crossed',
    ),
    Prompt(
        'Pointing forward decisively, determined confident expression, "let\'s do this" energy',
        'determined', ['pointing', 'decisive', 'lets-go'], 'determined-point',
    ),

    # ── EXCITED ───────────────────────────────────────────────────────
    Prompt(
        'Both fists raised in celebration, huge excited smile, jumping slightly, sparkles around',
        'excited', ['fist-pump', 'celebration', 'jumping', 'sparkles'], 'excited-fistpump',
    ),
    Prompt(
        'Arms spread wide in excitement, beaming smile, leaning forward enthusiastically, energetic happy pose',
        'excited', ['arms-wide', 'beaming', 'enthusiastic', 'energetic'], 'excited-armswide',
    ),
    Prompt(
        'Clapping hands together excitedly, big happy smile, bouncing on toes, joyful expression',
        'excited', ['clapping', 'bouncing', 'joyful'], 'excited-clapping',
    ),
    Prompt(
        'Pointing upward with one finger in "eureka!" moment, excited grin, lightbulb realization energy',
        'excited', ['pointing-up', 'eureka', 'lightbulb', 'realization'], 'excited-eureka',
    ),
    Prompt(
        'Arms raised in V-shape victory pose, huge smile, triumphant confident excited energy',
        'excited', ['victory', 'v-pose', 'triumphant'], 'excited-victory',
    ),
    Prompt(
        'Excited celebration with sparkles around, triumphant energy',
        'excited', ['celebration', 'sparkles', 'triumphant'], 'excited-celebrate',
        outfit_filter=['dress', 'sundress'],
    ),
    Prompt(
        'Controlled celebration, confident smile, arms crossed with satisfied expression, "I conquered this" triumph',
        'excited', ['controlled', 'satisfied', 'conquered', 'arms-crossed'], 'excited-controlled',
        outfit_filter=['teacher'],
    ),

    # ── FOCUSED ───────────────────────────────────────────────────────
    Prompt(
        'Hands positioned typing on keyboard, intense concentration, slight lean forward, in-the-zone focused',
        'focused', ['typing', 'keyboard', 'intense', 'zone'], 'focused-typing',
    ),
    Prompt(
        'Over-ear headphones, focused expression, hands on keyboard, deep concentration zone-out-the-world mode',
        'focused', ['headphones', 'keyboard', 'deep-focus'], 'focused-headphones',
    ),
    Prompt(
        'Hood up, intense focused expression, typing or hands together, deep concentration',
        'focused', ['hood-up', 'intense', 'deep-concentration'], 'focused-hoodup',
        outfit_filter=['hoodie'],
    ),

    # ── PLAYFUL ───────────────────────────────────────────────────────
    Prompt(
        'Both hands making finger gun gesture, playful wink, "ayyyy" confident cool energy',
        'playful', ['finger-guns', 'wink', 'confident', 'cool'], 'playful-fingerguns',
    ),
    Prompt(
        'Winking with tongue slightly out, one hand making peace sign, fun mischievous playful expression',
        'playful', ['wink', 'tongue', 'peace-sign', 'mischievous'], 'playful-wink-tongue',
    ),
    Prompt(
        'Finger to lips in "shh" gesture, playful secretive smile, cheeky energy',
        'playful', ['shh', 'finger-lips', 'secretive', 'cheeky'], 'playful-shh',
    ),
    Prompt(
        'Flirty playful smile, cute expression, mischievous happy energy',
        'playful', ['flirty', 'cute', 'mischievous'], 'playful-flirty',
    ),
    Prompt(
        'Playful wink, fun cheerful expression, lighthearted energy',
        'playful', ['wink', 'fun', 'lighthearted'], 'playful-wink',
    ),
    Prompt(
        'Sunglasses on, cool confident playful pose, laid-back fun energy',
        'playful', ['sunglasses', 'cool', 'confident', 'laid-back'], 'playful-sunglasses',
    ),
    Prompt(
        'One hand adjusting sunglasses with smirk, confident cool casual vibe',
        'playful', ['sunglasses', 'smirk', 'adjusting', 'cool'], 'playful-sunglasses-adjust',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),

    # ── SLEEPING / TIRED ──────────────────────────────────────────────
    Prompt(
        'Sleeping peacefully, counting sheep in thought bubble above head, "zzz" sleepy energy',
        'sleeping', ['zzz', 'thought-bubble', 'sheep', 'peaceful'], 'sleeping-sheep',
    ),
    Prompt(
        'Hand covering mouth in yawn, eyes closed or half-closed, tired but peaceful sleepy calm expression',
        'sleeping', ['yawn', 'hand-mouth', 'tired', 'peaceful'], 'sleeping-yawn',
    ),
    Prompt(
        'Arms raised above head in stretch pose, eyes closed contentedly, relaxed break-time calm energy',
        'calm', ['stretching', 'arms-up', 'eyes-closed', 'break'], 'calm-stretch',
    ),
    Prompt(
        'Slumped posture, heavy tired eyes but alert, one hand propping up head, late-night coding exhausted determination',
        'focused', ['slumped', 'tired', 'propping-head', 'late-night', 'coding'], 'focused-latenight',
    ),

    # ── SURPRISED ─────────────────────────────────────────────────────
    Prompt(
        'Hands up in surprised gesture, eyes wide, mouth open in surprise, startled expression',
        'surprised', ['hands-up', 'wide-eyes', 'startled', 'mouth-open'], 'surprised-startled',
    ),
    Prompt(
        'Eyes wide and bright with sudden realization, one finger raised, inspired "aha!" moment, lightbulb energy',
        'surprised', ['wide-eyes', 'finger-raised', 'aha', 'realization'], 'surprised-aha',
    ),

    # ── THINKING ──────────────────────────────────────────────────────
    Prompt(
        'Hand on cheek in thoughtful pose, pondering expression, considering carefully',
        'thinking', ['hand-cheek', 'pondering', 'considering'], 'thinking-cheek',
    ),
    Prompt(
        'One hand on chin thoughtfully, eyes looking up, contemplating pondering expression',
        'thinking', ['chin-touch', 'eyes-up', 'contemplating'], 'thinking-chin',
    ),
    Prompt(
        'Head tilted with one finger near chin, puzzled "wait what?" confused thinking expression',
        'thinking', ['head-tilt', 'finger-chin', 'puzzled', 'confused'], 'thinking-puzzled',
    ),

    # ── TEACHING / EXPLAINING ─────────────────────────────────────────
    Prompt(
        'One arm extended with open palm pointing gesture, confident smile, "let me show you" explaining teaching energy',
        'warm', ['explaining', 'palm-gesture', 'teaching', 'confident'], 'teaching-explain',
    ),
    Prompt(
        'One finger pointing forward or gesturing while explaining, confident teacher expression',
        'focused', ['pointing', 'explaining', 'teacher', 'gesturing'], 'teaching-point',
    ),
    Prompt(
        'Holding book or pointer, confident teaching expression',
        'focused', ['book', 'pointer', 'teaching', 'confident'], 'teaching-book',
        outfit_filter=['teacher'],
    ),

    # ── CASUAL GESTURES ───────────────────────────────────────────────
    Prompt(
        'Both hands raised in shrug gesture with palms up, slight smile, eyebrows raised, "idk" casual energy',
        'cheerful', ['shrug', 'palms-up', 'idk', 'casual'], 'casual-shrug',
    ),
    Prompt(
        'One hand raised to forehead in casual playful salute, determined smile, "on it!" ready-to-go expression',
        'determined', ['salute', 'ready', 'on-it'], 'casual-salute',
    ),
    Prompt(
        'One hand making peace sign, friendly casual smile, cool relaxed vibe',
        'cheerful', ['peace-sign', 'casual', 'cool', 'relaxed'], 'casual-peace',
    ),
    Prompt(
        'Fingers making OK gesture with thumb and index finger circle, approving satisfied smile',
        'cheerful', ['ok-sign', 'approving', 'satisfied'], 'casual-ok',
    ),
    Prompt(
        'One hand covering face in gentle embarrassed facepalm, peeking through fingers with sheepish smile',
        'apologetic', ['facepalm', 'embarrassed', 'peeking', 'sheepish'], 'casual-facepalm',
    ),
    Prompt(
        'Thumbs down gesture, disappointed but not angry expression, "that didn\'t work" reaction',
        'apologetic', ['thumbs-down', 'disappointed', 'failed'], 'casual-thumbsdown',
    ),
    Prompt(
        'Both thumbs up, confident cheerful smile, encouraging positive expression',
        'cheerful', ['thumbs-up', 'encouraging', 'positive', 'confident'], 'casual-thumbsup',
    ),

    # ── COFFEE / PROPS ────────────────────────────────────────────────
    Prompt(
        'Holding mug casually in one hand, relaxed neutral expression',
        'calm', ['mug', 'casual', 'relaxed', 'one-hand'], 'coffee-casual',
    ),
    Prompt(
        'Just-made-coffee happy energized cheerful expression, holding mug with excited smile',
        'cheerful', ['coffee', 'energized', 'excited', 'mug'], 'coffee-energized',
        outfit_filter=['dress', 'sundress', 'hoodie', 'pajamas'],
    ),
    Prompt(
        'Holding coffee mug with gentle caring expression, soft comforting smile, warm inviting energy',
        'warm', ['coffee', 'caring', 'comforting', 'mug'], 'coffee-caring',
    ),

    # ── LAPTOP / PHONE PROPS ─────────────────────────────────────────
    Prompt(
        'Laptop closed in front, taking a break, relaxed calm expression',
        'calm', ['laptop', 'break', 'relaxed'], 'laptop-break',
    ),
    Prompt(
        'Looking at laptop screen with happy surprised expression, exciting discovery energy',
        'surprised', ['laptop', 'discovery', 'happy-surprised'], 'laptop-discovery',
    ),
    Prompt(
        'Looking at phone in hands, neutral checking expression, casual scroll energy',
        'calm', ['phone', 'scrolling', 'casual', 'checking'], 'phone-scroll',
    ),
    Prompt(
        'Looking at phone with surprised excited expression at notification, "oh!" reaction',
        'surprised', ['phone', 'notification', 'excited', 'oh'], 'phone-notification',
    ),
    Prompt(
        'Holding phone to ear as if taking call, neutral conversational expression',
        'calm', ['phone', 'call', 'conversational'], 'phone-call',
    ),

    # ── HEADPHONES ────────────────────────────────────────────────────
    Prompt(
        'Over-ear headphones with eyes closed enjoying music, peaceful calm expression',
        'calm', ['headphones', 'music', 'eyes-closed', 'enjoying'], 'headphones-music',
    ),
    Prompt(
        'Headphones around neck casually, relaxed friendly expression',
        'cheerful', ['headphones', 'neck', 'casual', 'relaxed'], 'headphones-neck',
    ),

    # ── WAITING / IDLE ────────────────────────────────────────────────
    Prompt(
        'Neutral standing pose, patient waiting expression, calm composed',
        'waiting', ['standing', 'patient', 'composed'], 'waiting-standing',
    ),
    Prompt(
        'Arms crossed loosely, friendly waiting expression, relaxed patient pose',
        'waiting', ['arms-crossed', 'friendly', 'patient', 'relaxed'], 'waiting-crossed',
    ),
    Prompt(
        'Hands clasped together in front, sweet gentle waiting expression, patient stance',
        'waiting', ['clasped-hands', 'sweet', 'gentle', 'patient'], 'waiting-clasped',
    ),
    Prompt(
        'Adjusting hair flower with one hand, soft smile, casual waiting pose',
        'waiting', ['adjusting-hair', 'flower', 'soft-smile'], 'waiting-hairflower',
        outfit_filter=['dress', 'sundress', 'daisy-dukes'],
    ),
    Prompt(
        'Gentle idle sway, arms loose at sides, playful patient waiting expression',
        'waiting', ['idle', 'sway', 'playful', 'patient'], 'waiting-sway',
    ),

    # ── WARM / AFFECTIONATE ───────────────────────────────────────────
    Prompt(
        'Hands forming heart shape in front of chest, sweet warm smile, affectionate caring gesture',
        'warm', ['heart-hands', 'affectionate', 'sweet'], 'warm-heart',
    ),
    Prompt(
        'Hands clasped together near chest, sweet affectionate smile, warm caring expression',
        'warm', ['clasped-chest', 'affectionate', 'caring'], 'warm-clasped',
    ),
    Prompt(
        'One hand over heart, genuine warm smile, sweet affectionate expression',
        'warm', ['hand-heart', 'genuine', 'affectionate'], 'warm-handheart',
    ),
    Prompt(
        'Sweet innocent smile, hands clasped, warm gentle caring energy',
        'warm', ['innocent', 'clasped-hands', 'gentle', 'caring'], 'warm-innocent',
    ),
    Prompt(
        'Arms slightly open in welcoming hug gesture, warm gentle smile, inviting caring expression',
        'warm', ['open-arms', 'welcoming', 'hug', 'inviting'], 'warm-hug',
    ),
    Prompt(
        'Hands folded peacefully, soft content smile, warm understanding caring expression',
        'warm', ['folded-hands', 'content', 'understanding', 'peaceful'], 'warm-folded',
    ),

    # ── DETECTIVE ─────────────────────────────────────────────────────
    Prompt(
        'Sherlock Holmes deerstalker hat and holding magnifying glass, examining fingerprint or clue, detective investigation mode',
        'detective', ['deerstalker', 'magnifying-glass', 'investigating', 'sherlock'], 'detective-sherlock',
        outfit_filter=['dress', 'sundress'],
    ),

    # ── OUTFIT-SPECIFIC CASUAL ────────────────────────────────────────
    Prompt(
        'Casual comfortable pose, playful relaxed energy',
        'cheerful', ['casual', 'comfortable', 'playful', 'relaxed'], 'casual-comfortable',
    ),
    Prompt(
        'Cozy comfortable expression, casual energy',
        'warm', ['cozy', 'comfortable', 'casual'], 'casual-cozy',
    ),
    Prompt(
        'Graceful poised expression, sophisticated formal stance',
        'calm', ['graceful', 'poised', 'sophisticated', 'formal'], 'formal-graceful',
        outfit_filter=['ball-gown'],
    ),
    Prompt(
        'Sophisticated pose, confident elegant energy',
        'determined', ['sophisticated', 'confident', 'elegant'], 'formal-sophisticated',
        outfit_filter=['ball-gown'],
    ),
    Prompt(
        'Holding small clutch, elegant composed expression',
        'calm', ['clutch', 'elegant', 'composed'], 'formal-clutch',
        outfit_filter=['ball-gown'],
    ),
    Prompt(
        'Holding iced drink casually in one hand, content summer smile, refreshed cool energy',
        'cheerful', ['iced-drink', 'summer', 'refreshed', 'cool'], 'summer-iceddrink',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),
    Prompt(
        'One leg kicked up slightly behind, confident casual smile, relaxed happy pose',
        'cheerful', ['leg-kick', 'confident', 'casual', 'happy'], 'casual-legkick',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),
    Prompt(
        'Hands on hips confidently, bright smile, self-assured casual stance',
        'determined', ['hands-hips', 'confident', 'self-assured'], 'determined-hips',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),
    Prompt(
        'One hip cocked to side, casual confident waiting pose, relaxed stance',
        'waiting', ['hip-cock', 'confident', 'casual', 'relaxed'], 'waiting-hip',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),
    Prompt(
        'Casual comfortable lean against invisible wall, relaxed friendly expression',
        'cheerful', ['leaning', 'relaxed', 'friendly', 'casual'], 'casual-lean',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),
    Prompt(
        'Hands in back pockets casually, confident comfortable smile, laid-back energy',
        'cheerful', ['back-pockets', 'confident', 'laid-back'], 'casual-pockets',
        outfit_filter=['daisy-dukes'],
    ),
    Prompt(
        'Stretching arms overhead with happy content smile, enjoying summer day energy',
        'calm', ['stretching', 'overhead', 'content', 'summer'], 'casual-stretch-summer',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),
    Prompt(
        'Both hands pulling at hair in stress/frustration, wide eyes, flustered "why isn\'t this working" debugging panic',
        'surprised', ['hair-pull', 'frustrated', 'debugging', 'panic'], 'frustrated-debug',
        outfit_filter=['daisy-dukes'],
    ),
    Prompt(
        'Cozy relaxed content smile, comfortable bedtime energy',
        'warm', ['cozy', 'relaxed', 'bedtime', 'content'], 'pajama-cozy',
        outfit_filter=['pajamas'],
    ),
    Prompt(
        'Sleepy peaceful expression, ready for bed',
        'sleeping', ['sleepy', 'peaceful', 'bedtime'], 'pajama-sleepy',
        outfit_filter=['pajamas'],
    ),
    Prompt(
        'Holding phone to ear as if taking call, relaxed conversational summer chat',
        'calm', ['phone', 'call', 'summer', 'relaxed'], 'phone-summer',
        outfit_filter=['daisy-dukes', 'croptop', 'swimsuit'],
    ),

    # ── LUNA CREATIVE ADDITIONS ───────────────────────────────────────
    # New hairstyle-specific prompts, accessories, and moon-themed touches
    Prompt(
        'Hair swept dramatically by wind, confident determined gaze, billowing dynamic energy',
        'determined', ['wind-swept', 'dramatic', 'dynamic', 'billowing'], 'creative-windswept',
    ),
    Prompt(
        'Hair tucked behind one ear with shy smile, hand near ear, cute bashful expression',
        'warm', ['hair-tuck', 'shy', 'bashful', 'cute'], 'creative-hairtuck',
    ),
    Prompt(
        'Moon necklace glowing softly, one hand touching it gently, magical serene expression',
        'calm', ['moon-glow', 'necklace', 'magical', 'serene'], 'creative-moonglow',
    ),
    Prompt(
        'Sitting cross-legged floating slightly above ground, eyes closed, meditation moon energy aura',
        'calm', ['floating', 'meditation', 'moon-aura', 'cross-legged'], 'creative-moonmeditate',
    ),
    Prompt(
        'Stargazing upward with wonder-filled eyes, one hand reaching toward stars, dreamy amazed expression',
        'curious', ['stargazing', 'wonder', 'reaching', 'dreamy'], 'creative-stargazing',
    ),
    Prompt(
        'Reading a book intently, glasses slightly lowered on nose, absorbed focused expression',
        'focused', ['reading', 'book', 'glasses-lowered', 'absorbed'], 'creative-reading',
    ),
    Prompt(
        'Holding glowing crescent moon between both hands, magical sparkles, awed amazed expression',
        'excited', ['crescent-moon', 'glowing', 'magical', 'sparkles'], 'creative-holdmoon',
    ),
    Prompt(
        'Playful cat ears headband, paw gesture with one hand, mischievous cute "nya" expression',
        'playful', ['cat-ears', 'paw-gesture', 'nya', 'mischievous'], 'creative-catears',
    ),
    Prompt(
        'Flower crown of moonflowers and stars, gentle ethereal smile, soft dreamy fairy-tale energy',
        'warm', ['flower-crown', 'moonflower', 'ethereal', 'fairy-tale'], 'creative-flowercrown',
    ),
    Prompt(
        'Winking with finger gun and blown kiss effect, flirty confident playful energy, sparkle effects',
        'playful', ['wink', 'finger-gun', 'blown-kiss', 'sparkle'], 'creative-blownkiss',
    ),
    Prompt(
        'Dancing with arms gracefully extended, twirling motion blur on dress, joyful carefree expression',
        'excited', ['dancing', 'twirling', 'graceful', 'carefree'], 'creative-dancing',
    ),
    Prompt(
        'Painting on canvas with brush in hand, creative concentrated expression, artistic energy, paint splatters',
        'focused', ['painting', 'canvas', 'brush', 'artistic', 'creative'], 'creative-painting',
    ),
]
# fmt: on


# ============================================================================
# COSTUME-SPECIFIC PROMPTS (3-5 per costume)
# ============================================================================
# These are NOT multiplied by hairstyle variants. Each is specific to its costume.

# fmt: off
_COSTUME_PROMPTS: list[Prompt] = [
    # ── KNIGHT (applies to both knight-heavy and knight-light) ────────
    Prompt(
        'Sword raised overhead in battle-ready stance, fierce determined expression, shield braced at side',
        'determined', ['sword-raised', 'battle-ready', 'fierce', 'shield'], 'knight-battle',
        outfit_filter=['knight-heavy', 'knight-light'], is_costume=True,
    ),
    Prompt(
        'Kneeling with sword planted in ground, head bowed in noble oath, solemn determined pledge',
        'calm', ['kneeling', 'sword-planted', 'oath', 'noble'], 'knight-oath',
        outfit_filter=['knight-heavy', 'knight-light'], is_costume=True,
    ),
    Prompt(
        'Shield held forward in defensive guard stance, watchful alert expression, protecting something precious',
        'focused', ['shield-guard', 'defensive', 'alert', 'protecting'], 'knight-guard',
        outfit_filter=['knight-heavy', 'knight-light'], is_costume=True,
    ),
    Prompt(
        'Victorious pose with sword raised to sky, triumphant smile, moonlight reflecting off armor',
        'excited', ['victory', 'sword-sky', 'triumphant', 'moonlight'], 'knight-victory',
        outfit_filter=['knight-heavy', 'knight-light'], is_costume=True,
    ),
    Prompt(
        'Leaning on sword casually, friendly relaxed smile, armor slightly loosened, off-duty knight energy',
        'cheerful', ['leaning-sword', 'relaxed', 'off-duty', 'casual'], 'knight-casual',
        outfit_filter=['knight-heavy', 'knight-light'], is_costume=True,
    ),

    # ── COWGIRL ───────────────────────────────────────────────────────
    Prompt(
        'Spinning lasso overhead, wide confident grin, dynamic rope-twirling action pose',
        'excited', ['lasso', 'spinning', 'dynamic', 'action'], 'cowgirl-lasso',
        outfit_filter=['cowgirl'], is_costume=True,
    ),
    Prompt(
        'One hand tipping cowboy hat with wink, hip-shot stance, "howdy partner" flirty western greeting',
        'playful', ['hat-tip', 'wink', 'hip-shot', 'howdy'], 'cowgirl-howdy',
        outfit_filter=['cowgirl'], is_costume=True,
    ),
    Prompt(
        'Both revolvers drawn in quick-draw pose, focused sharp-shooter expression, wild-west showdown',
        'determined', ['quick-draw', 'revolvers', 'sharp-shooter', 'showdown'], 'cowgirl-quickdraw',
        outfit_filter=['cowgirl'], is_costume=True,
    ),
    Prompt(
        'Leaning against fence post casually, sunset glow behind, peaceful relaxed cowgirl at sunset',
        'calm', ['fence-lean', 'sunset', 'peaceful', 'relaxed'], 'cowgirl-sunset',
        outfit_filter=['cowgirl'], is_costume=True,
    ),
    Prompt(
        'Blowing across revolver barrel like clearing smoke, smirk, "too easy" confident cool energy',
        'playful', ['blowing-smoke', 'smirk', 'confident', 'cool'], 'cowgirl-smoke',
        outfit_filter=['cowgirl'], is_costume=True,
    ),

    # ── CYBERPUNK ─────────────────────────────────────────────────────
    Prompt(
        'Cybernetic arm raised showing holographic display, focused hacking expression, neon data streams',
        'focused', ['holographic', 'hacking', 'neon', 'data-streams'], 'cyber-hacking',
        outfit_filter=['cyberpunk'], is_costume=True,
    ),
    Prompt(
        'Leaning against neon-lit wall, tech glasses glowing, arms crossed, cyberpunk street attitude',
        'determined', ['neon-wall', 'glowing-glasses', 'arms-crossed', 'attitude'], 'cyber-street',
        outfit_filter=['cyberpunk'], is_costume=True,
    ),
    Prompt(
        'Cybernetic arm forming energy blade, combat-ready stance, intense focused expression',
        'determined', ['energy-blade', 'combat', 'intense', 'cybernetic'], 'cyber-combat',
        outfit_filter=['cyberpunk'], is_costume=True,
    ),
    Prompt(
        'Adjusting tech glasses with cybernetic hand, scanning expression, analyzing data overlay',
        'thinking', ['tech-glasses', 'scanning', 'analyzing', 'data'], 'cyber-scanning',
        outfit_filter=['cyberpunk'], is_costume=True,
    ),

    # ── PIRATE ────────────────────────────────────────────────────────
    Prompt(
        'Cutlass raised in one hand, parrot squawking on shoulder, triumphant "found the treasure!" grin',
        'excited', ['cutlass', 'parrot', 'treasure', 'triumphant'], 'pirate-treasure',
        outfit_filter=['pirate'], is_costume=True,
    ),
    Prompt(
        'Flintlock pistol aimed forward, one eye squinted, intense pirate dueling stance',
        'determined', ['flintlock', 'aiming', 'dueling', 'intense'], 'pirate-duel',
        outfit_filter=['pirate'], is_costume=True,
    ),
    Prompt(
        'Hand over eyes scanning the horizon from ship bow, determined captain expression, wind in hair',
        'focused', ['scanning-horizon', 'captain', 'ship-bow', 'wind'], 'pirate-horizon',
        outfit_filter=['pirate'], is_costume=True,
    ),
    Prompt(
        'Holding treasure map with excited expression, pointing at X marks the spot, adventurous grin',
        'excited', ['treasure-map', 'x-marks-spot', 'adventurous', 'pointing'], 'pirate-map',
        outfit_filter=['pirate'], is_costume=True,
    ),
    Prompt(
        'Hook hand raised menacingly with playful smirk, "arrr" pirate face, fun theatrical energy',
        'playful', ['hook-hand', 'arrr', 'theatrical', 'menacing'], 'pirate-arrr',
        outfit_filter=['pirate'], is_costume=True,
    ),

    # ── DETECTIVE ─────────────────────────────────────────────────────
    Prompt(
        'Magnifying glass held up examining a clue closely, intense focused investigation expression',
        'focused', ['magnifying-glass', 'clue', 'investigating', 'intense'], 'detective-clue',
        outfit_filter=['detective'], is_costume=True,
    ),
    Prompt(
        'Notebook in hand taking notes, pencil behind ear, thoughtful case-solving expression',
        'thinking', ['notebook', 'notes', 'pencil', 'case-solving'], 'detective-notes',
        outfit_filter=['detective'], is_costume=True,
    ),
    Prompt(
        'One finger raised in "elementary!" eureka moment, confident detective revelation smile',
        'excited', ['eureka', 'elementary', 'revelation', 'finger-raised'], 'detective-eureka',
        outfit_filter=['detective'], is_costume=True,
    ),
    Prompt(
        'Trench coat collar turned up, shadowy mysterious atmosphere, suspicious narrowed eyes',
        'focused', ['trench-coat', 'shadowy', 'mysterious', 'suspicious'], 'detective-mysterious',
        outfit_filter=['detective'], is_costume=True,
    ),

    # ── ELF ───────────────────────────────────────────────────────────
    Prompt(
        'Hands raised with swirling nature magic between palms, glowing green energy, serene casting expression',
        'calm', ['nature-magic', 'casting', 'glowing', 'green-energy'], 'elf-casting',
        outfit_filter=['elf'], is_costume=True,
    ),
    Prompt(
        'Graceful elvish bow with one hand on chest, elegant formal greeting, wise serene expression',
        'warm', ['bow', 'formal-greeting', 'elegant', 'wise'], 'elf-bow',
        outfit_filter=['elf'], is_costume=True,
    ),
    Prompt(
        'Listening intently with pointed ear tilted, communing with nature, peaceful forest energy',
        'calm', ['listening', 'pointed-ear', 'nature', 'peaceful'], 'elf-listening',
        outfit_filter=['elf'], is_costume=True,
    ),
    Prompt(
        'Holding glowing elvish artifact, reverent awed expression, ancient magic energy',
        'curious', ['artifact', 'glowing', 'reverent', 'ancient-magic'], 'elf-artifact',
        outfit_filter=['elf'], is_costume=True,
    ),

    # ── GOTH ──────────────────────────────────────────────────────────
    Prompt(
        'Arms crossed with dark confident smirk, black lipstick visible, "I am the night" goth energy',
        'determined', ['arms-crossed', 'smirk', 'dark-confident', 'night'], 'goth-night',
        outfit_filter=['goth'], is_costume=True,
    ),
    Prompt(
        'Holding black rose to nose, eyes closed, dark romantic melancholy expression, gothic beauty',
        'calm', ['black-rose', 'eyes-closed', 'melancholy', 'romantic'], 'goth-rose',
        outfit_filter=['goth'], is_costume=True,
    ),
    Prompt(
        'Sitting on ornate gothic chair, legs crossed, dark queen regal pose, imperious confident gaze',
        'determined', ['gothic-chair', 'regal', 'dark-queen', 'imperious'], 'goth-queen',
        outfit_filter=['goth'], is_costume=True,
    ),
    Prompt(
        'One hand twirling hair, bored dismissive expression with slight smirk, too-cool-for-this energy',
        'playful', ['hair-twirl', 'bored', 'dismissive', 'too-cool'], 'goth-bored',
        outfit_filter=['goth'], is_costume=True,
    ),

    # ── MAD SCIENTIST ─────────────────────────────────────────────────
    Prompt(
        'Holding bubbling flask up triumphantly, manic grin, "it works!" mad science eureka, green glow',
        'excited', ['flask', 'bubbling', 'manic-grin', 'eureka', 'green-glow'], 'scientist-eureka',
        outfit_filter=['mad-scientist'], is_costume=True,
    ),
    Prompt(
        'Goggles pushed up on forehead, wild hair, scribbling equations on whiteboard, intense focused frenzy',
        'focused', ['goggles', 'equations', 'whiteboard', 'frenzy'], 'scientist-equations',
        outfit_filter=['mad-scientist'], is_costume=True,
    ),
    Prompt(
        'Two test tubes clinking together in toast gesture, confident satisfied smirk, experiment success',
        'cheerful', ['test-tubes', 'toast', 'satisfied', 'experiment-success'], 'scientist-toast',
        outfit_filter=['mad-scientist'], is_costume=True,
    ),
    Prompt(
        'Explosion of colorful smoke behind, surprised but delighted expression, slightly singed, "oops but also wow"',
        'surprised', ['explosion', 'smoke', 'singed', 'delighted', 'oops'], 'scientist-explosion',
        outfit_filter=['mad-scientist'], is_costume=True,
    ),
    Prompt(
        'Pouring carefully between beakers, tongue sticking out in concentration, precise delicate lab work',
        'focused', ['pouring', 'beakers', 'tongue-out', 'concentration', 'precise'], 'scientist-pouring',
        outfit_filter=['mad-scientist'], is_costume=True,
    ),

    # ── SUPERHERO (applies to both variants) ──────────────────────────
    Prompt(
        'Classic superhero landing pose, one knee and fist on ground, cape billowing, powerful arrival',
        'determined', ['hero-landing', 'knee-fist', 'cape-billow', 'powerful'], 'hero-landing',
        outfit_filter=['superhero', 'superhero2'], is_costume=True,
    ),
    Prompt(
        'Hands on hips in classic superhero power pose, cape flowing, confident heroic smile, moon emblem glowing',
        'determined', ['power-pose', 'hands-hips', 'cape-flowing', 'heroic'], 'hero-powerpose',
        outfit_filter=['superhero', 'superhero2'], is_costume=True,
    ),
    Prompt(
        'Flying pose with one fist forward, cape streaming behind, determined soaring expression',
        'excited', ['flying', 'fist-forward', 'soaring', 'streaming-cape'], 'hero-flying',
        outfit_filter=['superhero', 'superhero2'], is_costume=True,
    ),
    Prompt(
        'Arms crossed floating in air, protective watchful guardian expression, moonlight aura around body',
        'focused', ['floating', 'arms-crossed', 'guardian', 'moonlight-aura'], 'hero-guardian',
        outfit_filter=['superhero', 'superhero2'], is_costume=True,
    ),

    # ── VAMPIRE ───────────────────────────────────────────────────────
    Prompt(
        'Cape dramatically swept to one side, fanged smile, hypnotic gaze, aristocratic vampire charm',
        'playful', ['cape-sweep', 'fanged-smile', 'hypnotic', 'aristocratic'], 'vampire-charm',
        outfit_filter=['vampire'], is_costume=True,
    ),
    Prompt(
        'Cape wrapped around self mysteriously, only eyes visible above, dramatic mysterious presence',
        'focused', ['cape-wrapped', 'eyes-only', 'mysterious', 'dramatic'], 'vampire-mystery',
        outfit_filter=['vampire'], is_costume=True,
    ),
    Prompt(
        'Hissing dramatically with cape spread wide, exaggerated theatrical vampire pose, playful spooky',
        'excited', ['hissing', 'cape-spread', 'theatrical', 'spooky'], 'vampire-hiss',
        outfit_filter=['vampire'], is_costume=True,
    ),
    Prompt(
        'Elegantly holding wine glass (red liquid), sophisticated vampire at a ball, refined aristocratic poise',
        'calm', ['wine-glass', 'sophisticated', 'ball', 'aristocratic'], 'vampire-ball',
        outfit_filter=['vampire'], is_costume=True,
    ),

    # ── WITCH ─────────────────────────────────────────────────────────
    Prompt(
        'Wand raised casting a spell, magical sparkles and stars swirling, intense focused casting expression',
        'focused', ['wand-raised', 'casting', 'sparkles', 'stars-swirling'], 'witch-casting',
        outfit_filter=['witch'], is_costume=True,
    ),
    Prompt(
        'Stirring large bubbling cauldron with ladle, mischievous grin, green magical steam rising',
        'playful', ['cauldron', 'stirring', 'mischievous', 'green-steam'], 'witch-cauldron',
        outfit_filter=['witch'], is_costume=True,
    ),
    Prompt(
        'Sitting on broomstick side-saddle, playful wave, ready to take flight, starry night background',
        'cheerful', ['broomstick', 'side-saddle', 'wave', 'starry-night'], 'witch-broom',
        outfit_filter=['witch'], is_costume=True,
    ),
    Prompt(
        'Holding open spellbook with glowing pages, reading intently, magical runes floating off pages',
        'thinking', ['spellbook', 'glowing-pages', 'reading', 'runes'], 'witch-spellbook',
        outfit_filter=['witch'], is_costume=True,
    ),
    Prompt(
        'Hat tipped low over one eye, sly knowing smile, mysterious witch-knows-something energy',
        'playful', ['hat-tipped', 'sly', 'mysterious', 'knowing'], 'witch-knowing',
        outfit_filter=['witch'], is_costume=True,
    ),

    # ── CONSTRUCTION ──────────────────────────────────────────────────
    Prompt(
        'Hammer raised about to nail, determined focused expression, building something, hard hat on',
        'determined', ['hammer', 'building', 'focused', 'hard-hat'], 'construct-build',
        outfit_filter=['construction'], is_costume=True,
    ),
    Prompt(
        'Reviewing blueprints held in both hands, thoughtful planning expression, safety vest visible',
        'thinking', ['blueprints', 'planning', 'reviewing', 'thoughtful'], 'construct-blueprints',
        outfit_filter=['construction'], is_costume=True,
    ),
    Prompt(
        'Big thumbs up with confident grin, hard hat slightly askew, "job done!" satisfied energy',
        'cheerful', ['thumbs-up', 'hard-hat', 'job-done', 'satisfied'], 'construct-thumbsup',
        outfit_filter=['construction'], is_costume=True,
    ),
    Prompt(
        'Wiping sweat from brow with forearm, tired but satisfied smile, hard day of work energy',
        'warm', ['wiping-sweat', 'tired', 'satisfied', 'hard-work'], 'construct-sweat',
        outfit_filter=['construction'], is_costume=True,
    ),
]
# fmt: on


# ============================================================================
# COMBINE ALL PROMPTS
# ============================================================================

MASTER_PROMPTS: list[Prompt] = _REGULAR_PROMPTS + _COSTUME_PROMPTS


# ============================================================================
# CROSS-PRODUCT MANIFEST BUILDER
# ============================================================================

def _get_regular_base_keys() -> list[str]:
    """Get all base image keys that are regular outfits (not costumes)."""
    return [k for k, v in BASE_IMAGES.items() if v['category'] == 'regular']


def build_manifest() -> list[dict]:
    """Build the full cross-product manifest.

    Regular prompts are multiplied by 4 hairstyle variants.
    Costume prompts are used as-is (no hairstyle multiplication).

    Returns:
        List of dicts with keys: base_key, base_file, prompt_text, emotion,
        tags, output_filename, output_dir, hairstyle.
    """
    manifest = []
    regular_keys = set(_get_regular_base_keys())

    # Pre-compute which outfit_keys have multiple base images (need disambiguator)
    from collections import Counter
    outfit_key_counts = Counter(v['outfit_key'] for v in BASE_IMAGES.values())
    shared_outfit_keys = {k for k, count in outfit_key_counts.items() if count > 1}

    for prompt in MASTER_PROMPTS:
        for base_key, base_info in BASE_IMAGES.items():
            if not prompt.applies_to(base_key):
                continue

            outfit_key = base_info['outfit_key']
            is_regular_base = base_key in regular_keys

            # Determine hairstyle variants to apply
            if prompt.is_costume or not is_regular_base:
                # Costume prompts or costume bases: no hairstyle multiplication
                variants = [HAIRSTYLE_VARIANTS[0]]  # just the original (no modifier)
            else:
                # Regular outfit + regular prompt: multiply by all 4 hairstyles
                variants = HAIRSTYLE_VARIANTS

            # Add disambiguator for bases sharing an outfit_key (e.g., knight-heavy/knight-light)
            base_suffix = f'-{base_key}' if outfit_key in shared_outfit_keys else ''

            for variant in variants:
                # Build the prompt text with hairstyle modifier
                prompt_text = prompt.text + variant['modifier']

                # Build filename
                filename = f'{outfit_key}-{prompt.filename_hint}{base_suffix}{variant["suffix"]}.png'

                # Build tags: emotion + outfit + prompt-specific + hairstyle + waiting
                tags = [prompt.emotion] + [outfit_key] + prompt.tags
                if variant['tag']:
                    tags.append(variant['tag'])
                if prompt.emotion in ('waiting', 'bored', 'sleeping'):
                    tags.append('waiting')

                manifest.append({
                    'base_key': base_key,
                    'base_file': base_info['file'],
                    'base_description': base_info['description'],
                    'prompt_text': prompt_text,
                    'emotion': prompt.emotion,
                    'tags': list(dict.fromkeys(tags)),  # dedupe preserving order
                    'output_filename': filename,
                    'output_dir': outfit_key,
                    'hairstyle': variant['tag'] or 'original',
                    'is_costume': prompt.is_costume,
                })

    return manifest


# ============================================================================
# PRIORITY SORTING - Preview Round System
# ============================================================================
# Generation order:
#   Phase 1: Preview Round - Regular Outfits (10 per outfit = 90 images)
#   Phase 2: Preview Round - Costumes (5 per costume = 70 images)
#   Phase 3: Complete dress collection (remaining ~386 images)
#   Phase 4: Everything else (remaining images, regular then costumes)
#
# Preview picks are selected algorithmically for maximum visual variety:
# spread across emotions, hairstyles, and prompt types.

PREVIEW_PER_REGULAR = 10
PREVIEW_PER_COSTUME = 5

# Emotions to prioritize in preview (most visually distinctive first)
_PREVIEW_EMOTION_PRIORITY = [
    'cheerful', 'excited', 'determined', 'playful', 'warm',
    'thinking', 'surprised', 'calm', 'curious', 'focused',
    'apologetic', 'sleeping', 'waiting', 'bored', 'detective',
]

_REGULAR_BASE_ORDER = [
    'dress', 'sundress', 'hoodie', 'daisy-dukes', 'croptop',
    'swimsuit', 'ball-gown', 'pajamas', 'teacher',
]

_COSTUME_BASE_ORDER = [
    'knight-heavy', 'knight-light', 'cowgirl', 'cyberpunk', 'pirate',
    'detective', 'elf', 'goth', 'mad-scientist', 'superhero',
    'superhero2', 'vampire', 'witch', 'construction',
]


def _select_preview_picks(entries: list[dict], count: int, prefer_costume_prompts: bool = False) -> list[dict]:
    """Select visually distinctive preview images from a set of entries.

    Spreads picks across different emotions and hairstyles for maximum variety.

    Args:
        entries: All manifest entries for a single base_key.
        count: Number of preview picks to select.
        prefer_costume_prompts: If True, prefer costume-specific prompts first.

    Returns:
        List of selected preview entries.
    """
    if len(entries) <= count:
        return list(entries)

    selected: list[dict] = []
    selected_set: set[str] = set()  # track by output_filename
    used_emotions: set[str] = set()
    used_hairstyles: set[str] = set()

    # For costumes: pick costume-specific prompts first (they're the most thematic)
    if prefer_costume_prompts:
        costume_specific = [e for e in entries if e.get('is_costume', False)]
        for entry in costume_specific:
            if len(selected) >= count:
                break
            if entry['emotion'] not in used_emotions or len(selected) < 3:
                selected.append(entry)
                selected_set.add(entry['output_filename'])
                used_emotions.add(entry['emotion'])
                used_hairstyles.add(entry.get('hairstyle', 'hair-down'))

    # Fill remaining slots by cycling through emotions and hairstyles
    for emotion in _PREVIEW_EMOTION_PRIORITY:
        if len(selected) >= count:
            break
        # Find entries with this emotion that haven't been selected
        candidates = [e for e in entries
                      if e['emotion'] == emotion and e['output_filename'] not in selected_set]
        if not candidates:
            continue

        # Prefer a hairstyle we haven't used yet
        for candidate in candidates:
            hair = candidate.get('hairstyle', 'hair-down')
            if hair not in used_hairstyles:
                selected.append(candidate)
                selected_set.add(candidate['output_filename'])
                used_emotions.add(emotion)
                used_hairstyles.add(hair)
                break
        else:
            # All hairstyles used, just pick the first candidate
            if candidates[0]['output_filename'] not in selected_set:
                selected.append(candidates[0])
                selected_set.add(candidates[0]['output_filename'])
                used_emotions.add(emotion)

    # If still short, fill with any remaining entries
    for entry in entries:
        if len(selected) >= count:
            break
        if entry['output_filename'] not in selected_set:
            selected.append(entry)
            selected_set.add(entry['output_filename'])

    return selected[:count]


def _sort_manifest(manifest: list[dict]) -> list[dict]:
    """Sort manifest with preview round priority.

    Order:
        1. Preview: 10 distinctive picks per regular outfit (90 images)
        2. Preview: 5 distinctive picks per costume (70 images)
        3. Remaining dress images (~386 images)
        4. Remaining regular outfit images
        5. Remaining costume images

    Args:
        manifest: Unsorted manifest entries.

    Returns:
        Sorted manifest with preview round first.
    """
    # Group all entries by base_key
    by_base: dict[str, list[dict]] = {}
    for entry in manifest:
        by_base.setdefault(entry['base_key'], []).append(entry)

    # Phase 1: Preview picks for regular outfits
    phase1_preview: list[dict] = []
    phase1_filenames: set[str] = set()
    for base_key in _REGULAR_BASE_ORDER:
        if base_key not in by_base:
            continue
        picks = _select_preview_picks(by_base[base_key], PREVIEW_PER_REGULAR)
        for p in picks:
            phase1_filenames.add((base_key, p['output_filename']))
        phase1_preview.extend(picks)

    # Phase 2: Preview picks for costumes
    phase2_preview: list[dict] = []
    phase2_filenames: set[str] = set()
    for base_key in _COSTUME_BASE_ORDER:
        if base_key not in by_base:
            continue
        picks = _select_preview_picks(by_base[base_key], PREVIEW_PER_COSTUME, prefer_costume_prompts=True)
        for p in picks:
            phase2_filenames.add((base_key, p['output_filename']))
        phase2_preview.extend(picks)

    # Phase 3: Remaining dress images (complete the dress collection)
    phase3_dress: list[dict] = []
    for entry in by_base.get('dress', []):
        if ('dress', entry['output_filename']) not in phase1_filenames:
            phase3_dress.append(entry)

    # Phase 4: Remaining regular outfit images (non-dress)
    phase4_regular: list[dict] = []
    for base_key in _REGULAR_BASE_ORDER:
        if base_key == 'dress' or base_key not in by_base:
            continue
        for entry in by_base[base_key]:
            if (base_key, entry['output_filename']) not in phase1_filenames:
                phase4_regular.append(entry)

    # Phase 5: Remaining costume images
    phase5_costume: list[dict] = []
    for base_key in _COSTUME_BASE_ORDER:
        if base_key not in by_base:
            continue
        for entry in by_base[base_key]:
            if (base_key, entry['output_filename']) not in phase2_filenames:
                phase5_costume.append(entry)

    result = phase1_preview + phase2_preview + phase3_dress + phase4_regular + phase5_costume

    # Tag each entry with its phase for stats display
    phase_idx = 0
    for entry in phase1_preview:
        entry['_phase'] = 'preview-regular'
        phase_idx += 1
    for entry in phase2_preview:
        entry['_phase'] = 'preview-costume'
    for entry in phase3_dress:
        entry['_phase'] = 'dress-complete'
    for entry in phase4_regular:
        entry['_phase'] = 'remaining-regular'
    for entry in phase5_costume:
        entry['_phase'] = 'remaining-costume'

    return result


MANIFEST = _sort_manifest(build_manifest())


# ============================================================================
# CHUNKING (for parallel Colab instances)
# ============================================================================

def get_chunk(chunk_index: int, total_chunks: int) -> list[dict]:
    """Get a specific chunk of the manifest for parallel execution.

    Chunks are split by base_key groups to keep all images for a single
    base image together (better for GPU cache and organization).

    Args:
        chunk_index: 0-based index of the chunk to get.
        total_chunks: Total number of chunks to split into.

    Returns:
        List of manifest entries for this chunk.

    Raises:
        ValueError: If chunk_index is out of range.
    """
    if chunk_index < 0 or chunk_index >= total_chunks:
        raise ValueError(f'chunk_index {chunk_index} out of range [0, {total_chunks})')

    # Group entries by base_key (preserving priority order)
    groups: list[tuple[str, list[dict]]] = []
    current_key = None
    current_group: list[dict] = []
    for entry in MANIFEST:
        if entry['base_key'] != current_key:
            if current_group:
                groups.append((current_key, current_group))
            current_key = entry['base_key']
            current_group = []
        current_group.append(entry)
    if current_group:
        groups.append((current_key, current_group))

    # Distribute groups across chunks (round-robin by cumulative size)
    chunk_assignments: list[list[dict]] = [[] for _ in range(total_chunks)]
    chunk_sizes = [0] * total_chunks
    for _key, group in groups:
        # Assign to the chunk with fewest entries so far
        smallest_chunk = min(range(total_chunks), key=lambda i: chunk_sizes[i])
        chunk_assignments[smallest_chunk].extend(group)
        chunk_sizes[smallest_chunk] += len(group)

    return chunk_assignments[chunk_index]


# ============================================================================
# STATS
# ============================================================================

def print_stats() -> None:
    """Print manifest statistics."""
    from collections import Counter

    regular_count = len(_REGULAR_PROMPTS)
    costume_count = len(_COSTUME_PROMPTS)
    est_secs = 25

    print(f'Base images: {len(BASE_IMAGES)} ({sum(1 for v in BASE_IMAGES.values() if v["category"] == "regular")} regular + {sum(1 for v in BASE_IMAGES.values() if v["category"] == "costume")} costumes)')
    print(f'Master prompts: {regular_count} regular + {costume_count} costume = {regular_count + costume_count} total')
    print(f'Hairstyle variants: {len(HAIRSTYLE_VARIANTS)}')
    print(f'Total manifest entries: {len(MANIFEST)}')
    print()

    # Phase breakdown
    phase_counts = Counter(m.get('_phase', 'unknown') for m in MANIFEST)
    phase_order = ['preview-regular', 'preview-costume', 'dress-complete', 'remaining-regular', 'remaining-costume']
    phase_labels = {
        'preview-regular': 'Phase 1: Preview - Regular Outfits',
        'preview-costume': 'Phase 2: Preview - Costumes',
        'dress-complete': 'Phase 3: Complete Dress Collection',
        'remaining-regular': 'Phase 4: Remaining Regular Outfits',
        'remaining-costume': 'Phase 5: Remaining Costumes',
    }
    print('Generation order:')
    cumulative = 0
    for phase in phase_order:
        count = phase_counts.get(phase, 0)
        cumulative += count
        hours = (count * est_secs) / 3600
        label = phase_labels.get(phase, phase)
        print(f'  {label}: {count} images (~{hours:.1f}h, cumulative: {cumulative})')
    print()

    # Preview round detail
    preview_entries = [m for m in MANIFEST if m.get('_phase', '').startswith('preview-')]
    print(f'Preview round total: {len(preview_entries)} images (~{len(preview_entries) * est_secs / 3600:.1f}h)')
    preview_by_base = Counter(m['base_key'] for m in preview_entries)
    for base_key in _REGULAR_BASE_ORDER + _COSTUME_BASE_ORDER:
        if base_key in preview_by_base:
            count = preview_by_base[base_key]
            # Show emotion variety for this base's preview picks
            base_preview = [m for m in preview_entries if m['base_key'] == base_key]
            emotions = [m['emotion'] for m in base_preview]
            hairs = [m.get('hairstyle', '?') for m in base_preview]
            unique_emotions = len(set(emotions))
            unique_hairs = len(set(hairs))
            print(f'  {base_key}: {count} picks ({unique_emotions} emotions, {unique_hairs} hairstyles)')

    # Per outfit
    print()
    outfit_counts = Counter(m['output_dir'] for m in MANIFEST)
    print('By outfit:')
    for outfit, count in outfit_counts.most_common():
        print(f'  {outfit}: {count} images')

    # Per emotion
    print()
    emotion_counts = Counter(m['emotion'] for m in MANIFEST)
    print('By emotion:')
    for emotion, count in emotion_counts.most_common():
        print(f'  {emotion}: {count} images')

    # Per hairstyle
    print()
    hair_counts = Counter(m['hairstyle'] for m in MANIFEST)
    print('By hairstyle:')
    for hair, count in hair_counts.most_common():
        print(f'  {hair}: {count} images')

    # Chunk preview
    print()
    print('Parallel chunk preview (3 chunks):')
    for i in range(3):
        chunk = get_chunk(i, 3)
        chunk_bases = Counter(m['base_key'] for m in chunk)
        bases_str = ', '.join(f'{k}({v})' for k, v in chunk_bases.most_common(5))
        print(f'  Chunk {i}: {len(chunk)} images [{bases_str}, ...]')


if __name__ == '__main__':
    print_stats()
