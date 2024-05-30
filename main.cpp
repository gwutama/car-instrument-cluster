#include <SDL2/SDL.h>
#include <SDL2/SDL_ttf.h>
#include <SDL2/SDL2_gfxPrimitives.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>
#include <thread>
#include <iostream>
#include <cmath>
#include <cstring>

#define WIDTH 1200
#define HEIGHT 600
#define RADIUS 225
#define SPEED_CAN_ID 0x1A0
#define RPM_CAN_ID 0x0AA

int speed = 0;
int rpm = 0;
bool running = true;
int can_socket;
struct sockaddr_can addr;
struct ifreq ifr;

SDL_Window *window = nullptr;
SDL_Renderer *renderer = nullptr;
TTF_Font *large_font = nullptr;
TTF_Font *normal_font = nullptr;
TTF_Font *small_font = nullptr;

SDL_Color BLACK = {0, 0, 0};
SDL_Color LIGHT_GRAY = {200, 200, 200};
SDL_Color DARK_GRAY = {100, 100, 100};
SDL_Color RED_ORANGE = {255, 51, 0};
SDL_Color DARK_RED_ORANGE = {128, 26, 0};
SDL_Color BLUE_PURPLE = {128, 0, 255};
SDL_Color DARK_PURPLE = {51, 0, 102};
SDL_Color LIGHT_PURPLE = {204, 153, 255};

bool init() {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        std::cerr << "SDL could not initialize! SDL_Error: " << SDL_GetError() << std::endl;
        return false;
    }

    if (TTF_Init() == -1) {
        std::cerr << "SDL_ttf could not initialize! TTF_Error: " << TTF_GetError() << std::endl;
        return false;
    }

    window = SDL_CreateWindow("Instrument Cluster", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, WIDTH, HEIGHT,
                              SDL_WINDOW_SHOWN);
    if (window == nullptr) {
        std::cerr << "Window could not be created! SDL_Error: " << SDL_GetError() << std::endl;
        return false;
    }

    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    if (renderer == nullptr) {
        std::cerr << "Renderer could not be created! SDL_Error: " << SDL_GetError() << std::endl;
        return false;
    }

    large_font = TTF_OpenFont("./conthrax-sb.otf", 55);
    normal_font = TTF_OpenFont("./conthrax-sb.otf", 20);
    small_font = TTF_OpenFont("./conthrax-sb.otf", 14);
    if (large_font == nullptr || normal_font == nullptr || small_font == nullptr) {
        std::cerr << "Failed to load font! TTF_Error: " << TTF_GetError() << std::endl;
        return false;
    }

    can_socket = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (can_socket < 0) {
        std::cerr << "Error while opening socket" << std::endl;
        return false;
    }

    strcpy(ifr.ifr_name, "vcan0");
    ioctl(can_socket, SIOCGIFINDEX, &ifr);

    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(can_socket, (struct sockaddr *) &addr, sizeof(addr)) < 0) {
        std::cerr << "Error in socket bind" << std::endl;
        return false;
    }

    return true;
}

void receive_can_data() {
    struct can_frame frame;
    while (running) {
        int nbytes = read(can_socket, &frame, sizeof(struct can_frame));
        if (nbytes > 0) {
            if (frame.can_id == SPEED_CAN_ID) {
                speed = ((frame.data[1] << 8) | frame.data[0]) * 0.103;
            } else if (frame.can_id == RPM_CAN_ID) {
                rpm = ((frame.data[5] << 8) | frame.data[4]) * 0.25;
            }
        }
    }
}

void draw_text(const std::string &text, int x, int y, TTF_Font *font, SDL_Color color) {
    SDL_Surface *surface = TTF_RenderText_Blended(font, text.c_str(), color);
    SDL_Texture *texture = SDL_CreateTextureFromSurface(renderer, surface);
    SDL_Rect dest_rect = {x, y, surface->w, surface->h};
    SDL_RenderCopy(renderer, texture, nullptr, &dest_rect);
    SDL_FreeSurface(surface);
    SDL_DestroyTexture(texture);
}

void draw_circle_glow(int center_x, int center_y, int inner_radius, int outer_radius, SDL_Color color) {
    for (int i = 0; i < (outer_radius - inner_radius); i++) {
        int alpha = static_cast<int>(255 * (1 - i / static_cast<float>(outer_radius - inner_radius)));
        aacircleRGBA(renderer, center_x, center_y, inner_radius + i, color.r, color.g, color.b, alpha);
    }
}

void
draw_gauge(int center_x, int center_y, int value, int max_value, int tick_min_value, int tick_max_value, int tick_step,
           const std::string &label) {
    // outer ring
    draw_circle_glow(center_x, center_y, RADIUS, RADIUS + 20, BLUE_PURPLE);

    // needle
    float angle = static_cast<float>(value) / max_value * 270 - 225;
    int x = center_x + (RADIUS - 95) * cos(angle * M_PI / 180.0);
    int y = center_y + (RADIUS - 95) * sin(angle * M_PI / 180.0);
    int x2 = center_x + RADIUS * cos(angle * M_PI / 180.0);
    int y2 = center_y + RADIUS * sin(angle * M_PI / 180.0);
    thickLineRGBA(renderer, x, y, x2, y2, 8, BLUE_PURPLE.r, BLUE_PURPLE.g, BLUE_PURPLE.b, 254);

    // inner ring
    aacircleRGBA(renderer, center_x, center_y, 130, BLUE_PURPLE.r, BLUE_PURPLE.g, BLUE_PURPLE.b, 254);
    draw_circle_glow(center_x, center_y, 130, 180, DARK_PURPLE);

    // ticks
    for (int i = tick_min_value; i <= tick_max_value; i += tick_step) {
        // main ticks
        SDL_Color tick_color = i >= tick_max_value - 2 * tick_step ? RED_ORANGE : LIGHT_GRAY;
        SDL_Color in_between_tick_color = i > tick_max_value - 3 * tick_step ? DARK_RED_ORANGE : DARK_GRAY;

        float angle = static_cast<float>(i - tick_min_value) / (tick_max_value - tick_min_value) * 270 - 225;
        int x1 = center_x + (RADIUS - 30 * 0.8) * cos(angle * M_PI / 180.0);
        int y1 = center_y + (RADIUS - 30 * 0.8) * sin(angle * M_PI / 180.0);
        int x2 = center_x + RADIUS * cos(angle * M_PI / 180.0);
        int y2 = center_y + RADIUS * sin(angle * M_PI / 180.0);
        aalineRGBA(renderer, x1, y1, x2, y2, tick_color.r, tick_color.g, tick_color.b, 254);

        // inbetween ticks
        if (i < tick_max_value) {
            float in_between_angle =
                    static_cast<float>(i + tick_step / 2 - tick_min_value) / (tick_max_value - tick_min_value) * 270 - 225;
            int in_between_x1 = center_x + (RADIUS - 20 * 0.8) * cos(in_between_angle * M_PI / 180.0);
            int in_between_y1 = center_y + (RADIUS - 20 * 0.8) * sin(in_between_angle * M_PI / 180.0);
            int in_between_x2 = center_x + RADIUS * cos(in_between_angle * M_PI / 180.0);
            int in_between_y2 = center_y + RADIUS * sin(in_between_angle * M_PI / 180.0);
            aalineRGBA(renderer, in_between_x1, in_between_y1, in_between_x2, in_between_y2, in_between_tick_color.r, in_between_tick_color.g, in_between_tick_color.b, 254);
        }

        // tick label
        float text_angle = static_cast<float>(i - tick_min_value) / (tick_max_value - tick_min_value) * 270 - 225;
        int text_x = center_x + (RADIUS - 60) * cos(text_angle * M_PI / 180.0);
        int text_y = center_y + (RADIUS - 60) * sin(text_angle * M_PI / 180.0);
        draw_text(std::to_string(i), text_x - 20, text_y - 10, small_font, DARK_GRAY);
    }

    // value
    int text_width = 0;
    TTF_SizeText(large_font, std::to_string(value).c_str(), &text_width, nullptr);
    draw_text(std::to_string(value), center_x - text_width / 2, center_y - 35, large_font, LIGHT_GRAY);
}

void main_loop() {
    SDL_Event e;
    SDL_Color background_color = {0, 0, 0, 255};

    while (running) {
        while (SDL_PollEvent(&e) != 0) {
            if (e.type == SDL_QUIT) {
                running = false;
            }
        }

        SDL_SetRenderDrawColor(renderer, background_color.r, background_color.g, background_color.b, 255);
        SDL_RenderClear(renderer);

        draw_gauge(300, 300, speed, 280, 0, 280, 20, "");
        draw_gauge(900, 300, rpm, 8000, 0, 8000, 1000, "");

        SDL_RenderPresent(renderer);
//        SDL_Delay(16); // Cap frame rate to ~60 FPS
    }
}

void destroy() {
    TTF_CloseFont(large_font);
    TTF_CloseFont(normal_font);
    TTF_CloseFont(small_font);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    TTF_Quit();
    SDL_Quit();
    close(can_socket);
}

int main(int argc, char *argv[]) {
    if (!init()) {
        std::cerr << "Failed to initialize!" << std::endl;
        return -1;
    }

    std::thread can_thread(receive_can_data);
    main_loop();

    running = false;
    can_thread.join();
    destroy();

    return 0;
}

