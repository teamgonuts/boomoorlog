/**
 * TypeScript types for the boomoorlog Supabase schema.
 *
 * Hand-written (NOT auto-generated). The Supabase CLI's `gen types` requires
 * Docker/Podman locally; for a 2-table schema it's faster to maintain by hand.
 * Keep in sync with db/001_schema.sql.
 *
 * If the schema changes, edit this file in the same PR as the migration.
 */

export type Database = {
  public: {
    Tables: {
      genera: {
        Row: {
          slug: string;
          latin_name: string;
          dutch_name: string | null;
          display_name: string | null;
          attack: number | null;
          range: number | null;
          health: number | null;
          attack_speed: number | null;
          move_speed: number | null;
          world_rarity_multiplier: number;
          avg_height_m: number | null;
          avg_diameter_cm: number | null;
          personality: string | null;
          tree_count: number;
          sprite_path: string | null;
          lore: string | null;
          created_at: string;
        };
        Insert: {
          slug: string;
          latin_name: string;
          dutch_name?: string | null;
          display_name?: string | null;
          attack?: number | null;
          range?: number | null;
          health?: number | null;
          attack_speed?: number | null;
          move_speed?: number | null;
          world_rarity_multiplier?: number;
          avg_height_m?: number | null;
          avg_diameter_cm?: number | null;
          personality?: string | null;
          tree_count?: number;
          sprite_path?: string | null;
          lore?: string | null;
          created_at?: string;
        };
        Update: Partial<Database["public"]["Tables"]["genera"]["Insert"]>;
      };
      trees: {
        Row: {
          id: number;
          genus_slug: string | null;
          species_full: string | null;
          species_top: string | null;
          postcode6: string | null;
          postcode4: string | null;
          buurt_id: string | null;
          longitude: number | null;
          latitude: number | null;
          rd_x: number | null;
          rd_y: number | null;
          geometrie_raw: string | null;
          height_class: string | null;
          diameter_class: string | null;
          height_m: number | null;
          diameter_cm: number | null;
          planting_year: number | null;
          owner: string | null;
          manager: string | null;
          location: string | null;
          location_detail: string | null;
          object_type: string | null;
          species_type: string | null;
          growing_location_id: string | null;
          protection_status: string | null;
          protection_status_detail: string | null;
          valid_from: string | null;
          mutated_at: string | null;
        };
        Insert: Database["public"]["Tables"]["trees"]["Row"];
        Update: Partial<Database["public"]["Tables"]["trees"]["Insert"]>;
      };
    };
  };
};

export type Genus = Database["public"]["Tables"]["genera"]["Row"];
export type Tree = Database["public"]["Tables"]["trees"]["Row"];
